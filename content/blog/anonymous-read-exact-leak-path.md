---
title: "The exact combination that leaks a bucket to the internet"
description: "Anonymous read needs a grant on the object, listing needs one on the bucket. Measured on a live endpoint one grant at a time, with the real error bodies."
date: 2026-11-20
author: "Clement Baranger"
tags: ["s3", "security", "public-access"]
guide: s3-error-codes
related: [bucket-policy-allow-still-denied, presigned-url-leakage]
---

## The short version

- A file in a bucket is readable by anyone when something attached to **the file** grants read to the group AWS calls All Users: an object ACL set to `public-read`, or a bucket policy whose `Principal` is `*`.
- Reading the **list of files** in the bucket is a different permission, attached to the bucket. A grant on a file never provides it, and a grant on the bucket never provides the file.
- The grants are independent. Deleting the policy does nothing to an ACL that is still in place, and Block Public Access only overrides grants while it is on: AWS documents that removing a switch makes the bucket public again.
- Measured on a live endpoint: the same bucket answers `403 AccessDenied` three times, then serves the bytes to an unsigned request, then goes back to `403` — one grant at a time, with the error body quoted below.
- The cost is not the incident: an enumerable bucket teaches a stranger your naming scheme, and each key found that way can be re-fetched from a CDN cache after the grant is gone.

## What actually happens

S3 decides each request separately, and "public" is not one setting — it is a property of the grant. An ACL is a list of grants to a canonical user or to a predefined group. Two groups make a resource public: `AllUsers`, which allows signed and unsigned requests, and `AuthenticatedUsers`, which allows any AWS account in the world as long as the request is signed ([AWS, ACL overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html)). A bucket policy becomes public when it grants a wildcard principal, or a principal scoped only by broad conditions.

The part people get wrong is the scope of the permission. The ACL permission `READ` means two different things depending on where it sits:

| Permission | On a bucket | On an object |
|---|---|---|
| `READ` | list the objects in the bucket | read the object data and its metadata |
| `WRITE` | create, overwrite and delete objects | not applicable |
| `FULL_CONTROL` | all of the above, plus the ACL | read and the ACL |

So `public-read` on a bucket hands out the **listing**. `public-read` on an object hands out **that file**. The canned ACL table lists both, and one line covers both scopes: `public-read` gives `AllUsers` `READ` ([canned ACLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl)).

![Three grants on a bucket: an object ACL and a policy Principal star expose the file to an unsigned GET, a bucket ACL exposes the listing, and Block Public Access overrides all of them without deleting them](/diagrams/anonymous-read-exact-leak-path.svg)

I ran the four states against a local endpoint that enforces authentication — a SeaweedFS 4.50 container started with an identities file, so an unsigned request is refused by default. The whole run is one script, `scripts/anon-access-probe.py`, and it prints this:

```
no grant                           GET 403 AccessDenied       LIST 403 AccessDenied       PUT 403 AccessDenied
object ACL public-read             GET 200                    LIST 403 AccessDenied       PUT 403 AccessDenied
bucket ACL public-read             GET 403 AccessDenied       LIST 200                    PUT 403 AccessDenied
policy: Principal * GetObject      GET 200                    LIST 403 AccessDenied       PUT 403 AccessDenied
policy deleted, ACLs private       GET 403 AccessDenied       LIST 403 AccessDenied       PUT 403 AccessDenied
```

Four things in that table matter.

**The object grant and the bucket grant do not overlap.** Row two exposes the file and leaves the listing closed; row three exposes the listing and leaves the file closed. That is not a quirk of the local server: it is exactly what the ACL permission table above says, and it is why "the bucket is private, I checked the ACL" and "the file is public" are both true at the same time.

**The policy and the ACL are the same door twice.** Rows two and four both produce `200`. Removing the policy in row five closes the object only because the ACL had already been reset. In an earlier pass of the same script I deleted the policy while the object ACL was still `public-read`, and the file kept answering `200`. Whichever grant you did not remove is the one still serving traffic.

**The 403 body is worth reading once.** The endpoint echoes the resource, the bucket and the key it refused:

```
<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>AccessDenied</Code><Message>Access Denied.</Message>
<Resource>/anon-probe-20261120/k.txt</Resource>
<RequestId>18E9BC0D634CC089…</RequestId>
<Key>k.txt</Key><BucketName>anon-probe-20261120</BucketName></Error>
```

That echo is a provider trait, not a guarantee, but it proves you reached the bucket: a `403` on a guessed name confirms the name exists.

**`PUT` stays closed in every row.** None of these grants carries `WRITE`. `public-read-write` on a bucket does, and AWS warns against it for a reason that costs money: anonymous uploads are owned by a sentinel canonical user id (`65a011a29cdf8ec533ec3d1ccaae921c`), so the bucket owner pays for objects they cannot attribute.

None of this explains a request that *should* have succeeded and came back `AccessDenied` anyway — that is a different chain, the [five-gate S3 evaluation order](/blog/bucket-policy-allow-still-denied).

## Where it bites

**Block Public Access is an override, not a delete.** AWS states it plainly: the settings "don't alter existing policies or ACLs. Therefore, removing a block public access setting causes a bucket or object with a public policy or ACL to again be publicly accessible" ([block public access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)). A bucket that has been public since 2019 and blocked since 2021 still carries the grant. Turn the four switches off during an incident debug and the original exposure returns with it.

**The four switches do different jobs, and one of them is redundant at the wrong level.**

- `BlockPublicAcls` makes `PutBucketAcl` and `PutObjectAcl` fail when the ACL is public, and `PutObject` fail when the request carries a public ACL. It changes nothing that already exists.
- `IgnorePublicAcls` accepts those calls and ignores the resulting grants at evaluation time — so the ACL reads as public and authorises nothing.
- `BlockPublicPolicy` rejects a `PutBucketPolicy` whose document is public. AWS notes the trap: a bucket policy can grant the right to change the bucket policy, so this switch protects little when applied per bucket. Apply it at account level.
- `RestrictPublicBuckets` is the blunt one. Once any statement in the policy makes it public, it blocks all public **and** cross-account access — including the specific-account statement you were relying on. AWS's example: a policy granting CloudTrail, a named account, and `*` lets only CloudTrail through.

**On new AWS buckets the ACL half is already closed.** Object Ownership defaults to `Bucket owner enforced`, ACL writes fail with `AccessControlListNotSupported`, and the policy becomes the only way to leak — a policy written in 2020 is untouched by any of it. S3-compatible servers are not bound by that default: the run above honoured ACLs, and a SeaweedFS started *without* an identities file answered `200` to an unsigned GET with no policy at all.

**`AuthenticatedUsers` is not a safe substitute for `AllUsers`.** It allows any AWS account, signed only. It is a public grant with an extra step.

## Doing it right

**1. Ask from outside, without credentials.** This is the only test that answers the question the internet asks:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  https://warehouse-prod.s3.eu-west-3.amazonaws.com/payroll.csv
curl -s -o /dev/null -w '%{http_code}\n' \
  'https://warehouse-prod.s3.eu-west-3.amazonaws.com/?list-type=2'
```

`200` on the first means the object is exposed. `200` on the second means the bucket is enumerable. Both `403` and you can stop reading.

**2. Read the three grant locations, not one.**

```bash
aws s3api get-bucket-acl --bucket warehouse-prod --query 'Grants[?Grantee.URI!=null]'
aws s3api get-bucket-policy --bucket warehouse-prod --query Policy --output text | jq .
aws s3api get-bucket-policy-status --bucket warehouse-prod
```

A `Grantee.URI` ending in `AllUsers` or `AuthenticatedUsers` is a public grant. An empty first command with a non-empty second one means the policy is the door. `IsPublic: true` confirms the stored policy qualifies as public even while a switch is neutralising it.

**3. Reproduce the matrix on a throwaway endpoint before you touch production.** One grant per row, one row at a time, tells you which grant is actually serving the request:

```bash
python3 -m venv /tmp/s3probe && /tmp/s3probe/bin/pip install boto3
/tmp/s3probe/bin/python scripts/anon-access-probe.py \
  --endpoint http://127.0.0.1:18335 --bucket anon-probe --access-key probe --secret-key probesecret
```

**4. Remove the grant, keep the switch.** Disable ACLs on the bucket (`Bucket owner enforced`) and delete any statement whose principal is `*` in the same change. Turning a Block Public Access switch off instead is a change that reads like a fix and restores the exposure.

**5. Re-run step 1 until both lines answer `403`, then look for copies.** A leaked key has already been fetched — and it carries the copies that make [a presigned link impossible to withdraw](/blog/presigned-url-leakage). Check the CDN cache, the access logs, the link previews in chat, and any website endpoint still pointing at the same prefix.

## How S3 Explorer fits

Every connection profile in [S3 Explorer](https://s3explorer.accessdevops.com) keeps its own endpoint, region, addressing style and credentials, and the **Test connection** button reports how many buckets those credentials can actually see before the profile is saved — so the key you suspect of being over-scoped gets its own profile and an immediate count, without disturbing the admin profile you were using. Browsing that profile also drives the per-request metrics dashboard, which counts the `LIST` and `GET` calls the session generated: opening a bucket you believe is closed and watching the listing come back is more convincing than reading a policy document.

## Checklist

- [ ] `curl` with no credentials returns `403` for both the object and the listing
- [ ] No grant in `get-bucket-acl` names `AllUsers` or `AuthenticatedUsers`
- [ ] `get-bucket-policy` has no statement with `Principal: "*"` and no broad `aws:SourceIp`
- [ ] Object Ownership is `Bucket owner enforced`, so ACLs cannot be reintroduced
- [ ] All four Block Public Access settings are on at account level, not only per bucket
- [ ] The `403` was reproduced after the change, not assumed from the console
- [ ] CDN and website endpoints on the same prefix were checked for copies
- [ ] Anyone who received a link to a leaked key was told, not just the bucket owner
