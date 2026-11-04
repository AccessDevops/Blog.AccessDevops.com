---
title: "Presigned URLs leak into logs, referrers and chat"
description: "A presigned URL is a working credential stored as text. Where the copy ends up, what it still grants after redaction, and the 15-minute fix."
date: 2026-11-04
author: "Clement Baranger"
tags: ["s3", "security", "presigned-urls"]
guide: share-s3-file-presigned-url
related: [presigned-url-seven-day-ceiling, presigned-post-enforce-size-content-type]
---

A support ticket reads: "the invoice link does not work". The link was pasted into the ticket by an engineer, copied into a CRM note by a salesperson, and fetched by the mail gateway that scanned the ticket. Three copies of a valid credential, in three systems that keep text for years, and one expiry date that nobody in the conversation controls.

## The short version

- A presigned URL is not a link to a file. It is a signature — a working credential written into the address of the object.
- Anyone holding the string can fetch the object until the moment written inside it. No password, no identity check, no record of who used it.
- Measured today with botocore 1.43: a 900-second `GET` link is **334 characters**, **1 009** when signed with a session token. The signature is 64 of those characters, and it is the only part that grants access.
- Every system that stores URIs keeps a copy — access log, CDN, WAF, TLS proxy, the chat client that builds a preview, the ticket where it was pasted — and most keep it for a year, redacting nothing.
- Kill one leaked URL by deleting its access key and every other live link signed with that key dies in the same second.

## What actually happens

Presigning is arithmetic performed on the client: a canonical request is hashed with a key derived from the secret access key, the date, the region and the service, and the result is appended to the URL. No API call is made — which is why it works offline, and why nobody can stop you from generating a bad one.

That also means the credential is readable text. Building a URL with a throwaway key pair and printing its parameters gives the inventory:

```bash
python3 -m venv presign-venv && ./presign-venv/bin/pip -q install boto3
```

```python
# presign-one.py — no AWS account, no network: fake keys produce a valid structure
import boto3, urllib.parse
from botocore.config import Config

s3 = boto3.client("s3",
    aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region_name="eu-west-3",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))

url = s3.generate_presigned_url("get_object",
    Params={"Bucket": "docs-prod", "Key": "contracts/acme-2026.pdf"}, ExpiresIn=900)

print(len(url))                                    # 334
for k, v in urllib.parse.parse_qsl(urllib.parse.urlparse(url).query):
    print(f"{k:24} {len(v):4}  {urllib.parse.unquote(v)[:60]}")
```

The output, trimmed to the columns that matter:

```text
X-Amz-Algorithm          value=16  AWS4-HMAC-SHA256
X-Amz-Credential         value=55  <access key id>/20261104/eu-west-3/s3/aws4_request
X-Amz-Date               value=16  20261104T110619Z
X-Amz-Expires            value=3   900
X-Amz-SignedHeaders      value=4   host
X-Amz-Signature          value=64  4b4ec51ce28bf30ce5e92301ee45a6...
```

Three things follow from that listing, and none of them is visible when the URL is a blue link in a chat window.

**The URL names the principal.** `X-Amz-Credential` carries the access key ID in clear, with the signing date, region and service. A leaked URL tells the reader which key to hunt for. Signed with temporary credentials, the same query string carries `X-Amz-Security-Token` — 653 characters in the same test, taking the URL to 1 009. That token is not a credential on its own, since SigV4 still needs the matching secret, but it pins the session: a log reader knows which role signed the link and when it ends.

**Only one header is signed.** `X-Amz-SignedHeaders` is `host`. Everything else — `Range`, `User-Agent`, conditional headers — can be added or changed by whoever holds the URL. A 5 GB object behind a 15-minute link is not a 15-minute download: it is as many ranged requests as the holder cares to send inside the window. AWS documents the mirror image in its FAQ — once `Range` *is* signed, S3 demands `If-Range` be signed too, and answers `AccessDenied` with `HeadersNotSigned: if-range` when it is not.

**There is no handle to revoke.** AWS states the position plainly: "In essence, presigned URLs are bearer tokens that grant access to those who possess them." The server never asks who is calling. There is no list of issued URLs, no per-URL delete, no IP binding, no single-use mode — only the expiry inside the link and the validity of the credential behind it.

![Diagram: a presigned URL leaves the signer and is copied into four stores — an application log, a CDN log, a TLS proxy and a chat preview — with the signature granting access until expiry](/diagrams/presigned-url-leakage.svg)

## Where it bites

The interesting part is not that a URL can leak. It is that the industry-standard mitigation removes the wrong half.

AWS's prescriptive guidance on presigned URLs recommends redacting the `X-Amz-Signature` parameter from any URI log, and says S3 does it: "Amazon S3 server access logs include the request URI but redact the `X-Amz-Signature` … The same is true when CloudTrail data events are logged for Amazon S3." Applying the published regex `X-Amz-Signature=[a-f0-9]{64}` to the URL above leaves this:

```text
https://docs-prod.s3.eu-west-3.amazonaws.com/contracts/acme-2026.pdf
  ?X-Amz-Algorithm=AWS4-HMAC-SHA256
  &X-Amz-Credential=<key id>%2F20261104%2Feu-west-3%2Fs3%2Faws4_request
  &X-Amz-Date=20261104T110534Z
  &X-Amz-Expires=900
  &X-Amz-SignedHeaders=host
  &X-Amz-Signature=XXXXXXXX…XXXXXXXX
```

Redaction kills replay, which is the important half. It does not hide the key ID, the signing date, the region, the expiry, or the session token. A log therefore remains an identity disclosure after redaction, and its reader learns which credential to attack — a smaller problem than a live link, and a much larger one than zero.

| Where the URL is written | What survives | What it costs you |
|---|---|---|
| Application access log (`nginx`, API gateway) | The whole query string by default | A year of replayable links on disk |
| S3 server access log, CloudTrail data events | URI with `X-Amz-Signature` redacted | Identity and expiry disclosure only |
| CDN, WAF, load-balancer logs | Usually the full URI | The same, in a system with wider read access |
| TLS-inspecting proxy, mail gateway | Full URI, plus the body | The proxy team holds your links |
| Chat client, ticket, CRM, PDF | The literal string, forever | Outlives every retention policy on the bucket |

Two failure modes hide in that table.

**The link preview that spends the link.** Paste a presigned URL into a chat client or a ticketing tool and that service fetches it to render a preview or scan for malware. The request is real and appears in your access logs, so the first "click" in your analytics is a bot from a datacentre IP you do not recognise.

**The seven-day window nobody chose.** Asked for "a link that works for a month", the SDK returns the maximum instead of an error. That link then sits in a log for a week, which is where redaction is the only thing between a log reader and the object. The mechanics of that ceiling, and the three other clocks that shorten a link, are in [Presigned URLs expire at seven days. Then what?](/blog/presigned-url-seven-day-ceiling).

Upload URLs fail differently, because the signed policy is the whole document. A presigned `PUT` that does not pin content type and size hands the holder permission to write any file of any size under that key — the mechanism and the exact condition syntax are in [Presigned POST: cap size and type before the upload starts](/blog/presigned-post-enforce-size-content-type).

## Doing it right

**1. Shorten the window until it hurts.** Fifteen minutes covers a click-through. Anything longer is a decision, not a default. Measure what you actually issue rather than what you asked for:

```bash
grep -o 'X-Amz-Expires=[0-9]*' /tmp/presigned.url
```

**2. Put a floor under the TTL at the bucket.** The `s3:signatureAge` condition key caps how old a signature may be, regardless of what the URL claims. It is expressed in **milliseconds** — 900 000 is fifteen minutes, not 900 seconds — and AWS notes that values below 60 seconds produce random failures on clock skew:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyPresignedOver15Minutes",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": "arn:aws:s3:::docs-prod/*",
    "Condition": { "NumericGreaterThan": { "s3:signatureAge": "900000" } }
  }]
}
```

A `Deny` beats any `Allow`, whatever the order of the statements, which is why a bucket policy is the right place for this and not the application.

**3. Deny query-string authentication where it is never needed.** `s3:authType` distinguishes header-signed requests (`REST-HEADER`) from presigned ones (`REST-QUERY-STRING`). Buckets that are only read by services can refuse every presigned request outright:

```json
{
  "Sid": "DenyNonHeaderAuth",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": "arn:aws:s3:::docs-prod/*",
  "Condition": { "StringNotEquals": { "s3:authType": "REST-HEADER" } }
}
```

AWS warns about the side effect: the S3 console downloads objects with presigned URLs, so on a bucket carrying this statement the console's Download button stops working for everyone without an exception.

**4. Redact in your own logs, then check that you did.** AWS publishes the pattern; use it in the log format rather than in a downstream parser you will forget to update.

```bash
# nginx: map the query away before it reaches the log line
map $args $safe_query {
    default            "";
    "~^(?<keep>.*)X-Amz-Signature=[a-f0-9]{64}(?<rest>.*)$"  "$keep""X-Amz-Signature=REDACTED""$rest";
}
log_format redacted '$remote_addr "$request_method $uri?$safe_query" $status';

# and prove it on the files you already have
grep -rlE 'X-Amz-Signature=[a-f0-9]{64}' /var/log/ /var/awslogs/ 2>/dev/null | head
```

That `grep` is the audit: every file it prints holds live credentials for the length of their TTL.

**5. Make single-use links real, in your own state.** S3 has no single-use mode. A nonce table is enough: mint the URL behind your own authentication, store a hash of the nonce with the object key, delete the row on the first successful redirect to S3. A second request with the same nonce gets a 410 from your server, not from S3.

**6. Do not try to bind a URL to an IP.** You cannot put an IP into the signature. What you can do is restrict the signing principal with `aws:SourceIp` — evaluated at request time against the address the request arrives from, not the address of the service that signed it.

## How S3 Explorer fits

When a link fails, the question is which credential signed it, against which endpoint, and whether that key still sees the bucket. S3 Explorer's connection form takes a display name, endpoint, region, path-style toggle and credentials, and **Test connection** reports how many buckets those credentials can actually see before you save the profile — the difference between an expired link and a key that lost its permission. The **per-request metrics dashboard** counts the session's API calls by category, turning a wall of 403s into a number, and switching between connection profiles puts production and staging side by side. [S3 Explorer](https://s3explorer.accessdevops.com) runs on Windows, macOS and Linux.

## Checklist

- [ ] Every `generate_presigned_url` call site passes an explicit `ExpiresIn`, and no value exceeds 900.
- [ ] `grep -rE 'X-Amz-Signature=[a-f0-9]{64}'` over your log directories returns nothing.
- [ ] A bucket policy `Deny` on `s3:signatureAge` (milliseconds) exists on every bucket that issues links.
- [ ] Buckets read only by services carry the `s3:authType` deny, with console users exempted if they need it.
- [ ] Single-use links are enforced by a nonce table on your side, not by hoping.
- [ ] The signing credential is dedicated, temporary, and scoped to the prefix that needs it.
- [ ] Support and sales know that a pasted link is a credential: the runbook says rotate, not "wait for it to expire".
- [ ] You have replayed a redacted log line and seen which fields are still readable.

## Sources

- [AWS Prescriptive Guidance — Logging interactions and mitigations](https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/logging-interactions.html): the bearer-token framing, the S3 access-log and CloudTrail redaction of `X-Amz-Signature`, and the `X-Amz-Signature=[a-f0-9]{64}` pattern.
- [AWS Prescriptive Guidance — Additional guardrails](https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/additional-guardrails.html): `s3:signatureAge` in milliseconds, the 60-second practical floor, `s3:authType` `REST-QUERY-STRING` versus `REST-HEADER`, and the console caveat.
- [AWS Prescriptive Guidance — Foundational best practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/foundational-best-practices.html): `aws:SourceIp` evaluated at request time from the requesting system.
- [Amazon S3 — Download and upload objects with presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html): "presigned URLs are bearer tokens", the console's 1-minute-to-12-hour range, the `HeadersNotSigned: if-range` error.
- [Amazon S3 — Server access log format](https://docs.aws.amazon.com/AmazonS3/latest/userguide/LogFormat.html): the `Request-URI` field example carrying a query string, and `Authentication Type` = `QueryString` for presigned requests.

Measurements taken on 4 November 2026 with botocore 1.43.123, `eu-west-3`, virtual-hosted addressing, bucket `docs-prod`, key `contracts/acme-2026.pdf`, `ExpiresIn=900`; the key pair is the AWS documentation placeholder, never a real credential.
