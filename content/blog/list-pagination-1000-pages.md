---
title: "S3 LIST returns 1,000 entries a page, folders included"
description: "One ListObjectsV2 response holds at most 1,000 entries, and a folder rollup spends one of them. Measured on two endpoints, plus the loop that stops too early."
date: 2026-11-11
author: "Clement Baranger"
tags: ["s3", "api", "performance"]
guide: s3-compatible-storage-desktop-client
related: [s3-total-cost-of-ownership, s3-explorer-walkthrough]
---

A cleanup script lists a bucket, deletes what it finds, prints `done`, and leaves 97% of the objects in place. Nothing errored. The script asked for the bucket contents once, received a page of 1,000 entries, and treated that page as the bucket. Every S3-compatible endpoint behaves this way, and the response says so — in `IsTruncated`, a field most code never reads.

## The short version

- One list request returns at most 1,000 entries. A bucket holding ten million objects takes ten thousand requests to walk.
- A folder in the response is one of those 1,000 entries. A page can come back with 10 folders and 990 files, and still be full.
- The end of a listing is signalled by `IsTruncated: false`. A page shorter than `MaxKeys` is not the end.
- Asking for `max-keys=5000` returns 1,000 entries on a real endpoint and 2,501 on the mock server most tests use — so a passing test proves nothing about production.
- Ten million objects is 10,000 billed requests to enumerate: $0.045 on Cloudflare R2 at $4.50 per million Class A operations. The script that misses objects costs more than the listing.

## What actually happens

`ListObjectsV2` answers with a page. The API reference opens with "Returns some or all (up to 1,000) of the objects in a bucket with each request", and the `MaxKeys` parameter repeats it: "By default, the action returns up to 1,000 key names. The response might contain fewer keys but will never contain more."

So 1,000 is not a default you can raise. It is the width of the pipe. Two fields describe what came back: `Contents`, the objects, and `KeyCount`, the number of entries the page actually carried. A third, `IsTruncated`, says whether another page exists, and `NextContinuationToken` — "obfuscated and is not a real key" — carries the position forward.

The ceiling costs nothing per object: AWS's own guidance says list performance "is not substantially affected by the total number of keys in your bucket". A million keys and a thousand keys answer in the same time. What changes is how many round trips you need, and each one is billed.

![Three ListObjectsV2 requests over 2,501 keys returning 1,000, 1,000 and 501 entries, then the same bucket listed with a delimiter where 990 objects and 10 folders together fill the 1,000-entry budget, so a loop comparing the object count with MaxKeys exits after one page](/diagrams/list-pagination-1000-pages.svg)

Now the part that breaks code. Add `delimiter=/` and the response rolls up everything under a common prefix into a single `CommonPrefixes` entry, the thing a GUI draws as a folder. The API reference is explicit that the rollup is not free: "Each rolled-up result counts as only one return against the MaxKeys value." A page is therefore up to 1,000 *entries*, not 1,000 objects, and the mix is whatever the key order produces.

## Where it bites

I filled a bucket with a known layout and paged through it on two endpoints: SeaweedFS 4.50 (`weed server -s3`, S3 gateway on a local port) and moto 5.2.5, the Python mock that a large share of S3 test suites run against. Both were queried with `boto3` 1.44.0 on 11 November 2026.

| Endpoint | 2,501 keys under `flat/` | `max-keys=5000` | `delimiter=/` over `mixed/` | Token returned |
|---|---|---|---|---|
| SeaweedFS 4.50 | 3 pages: 1,000 / 1,000 / 501 | 1,000 entries, `IsTruncated: true` | 990 `Contents` + 10 `CommonPrefixes`, `KeyCount` 1,000, `IsTruncated: true` | the last key, `flat/0999` |
| moto 5.2.5 | 3 pages: 1,000 / 1,000 / 501 | **2,501 entries**, `IsTruncated: false` | identical: 990 + 10, `KeyCount` 1,000 | 32 hex characters |

```bash
python3 scripts/list-pagination-probe.py fill http://127.0.0.1:8333 listprobe
python3 scripts/list-pagination-probe.py run  http://127.0.0.1:8333 listprobe
```

**The most expensive bug is a comparison against `MaxKeys`.** The page over `mixed/` came back with 990 objects and 10 folders. It is completely full — `KeyCount` is 1,000 — but `len(Contents)` is 990, so `if len(Contents) < MaxKeys: break` exits after one request. In this layout the 40 folders that were never listed hold another 2,000 keys. The script reports success because no call failed. Both endpoints produced this page identically; it is not a quirk, it is the contract.

**`max-keys` above 1,000 is a request, not a setting.** SeaweedFS clamped it to 1,000 and set `IsTruncated: true`. moto returned all 2,501 entries in one response and set `IsTruncated: false` — behaviour AWS's documentation rules out. A test suite on the mock sees a complete listing from a single call, then production hands the same code 1,000 entries and a token it ignores.

**`max-keys=0` returns an empty page with `IsTruncated: false` on both endpoints** — the probe for "how many objects are here" reads `KeyCount`, gets zero, and reports an empty bucket with no error.

**Order is UTF-8 binary, not sensible.** The five keys `order/1`, `order/2`, `order/9`, `order/10`, `order/100` came back as `1, 10, 100, 2, 9`. Date-suffixed keys sort wrong at the month boundary (`2026-11-1` before `2026-11-10` before `2026-11-2`), and numeric IDs sort as text. Anything that pages by "last key seen" inherits that order, so a resumable job restarts in the wrong place when the naming scheme is numeric.

**The token looks like a key on one endpoint and a hash on the other.** SeaweedFS answered `NextContinuationToken: flat/0999` — the last key of the page. moto answered a 32-character hex string. Code that treats the token as `StartAfter`, or persists it across an upgrade, works on the self-hosted server and fails on AWS. AWS documents the token as obfuscated; its shape is not part of the contract.

**Browsing is not free either.** AWS bills LIST requests in the same class as PUT, and the pricing page states that browsing the console "incur[s] charges for GET, LIST, and other requests that are made to facilitate browsing". A person clicking through folders generates exactly the calls a script does — [the S3 Explorer walkthrough](/blog/s3-explorer-walkthrough) shows that browse call by call — and the invoice consequence is set out in [the request charges that make up most of an S3 bill](/blog/s3-total-cost-of-ownership).

## Doing it right

**1. Loop on `IsTruncated` and nothing else.** The SDK paginator does it for you; hand-rolled loops should copy its shape exactly.

```python
paginator = s3.get_paginator("list_objects_v2")
total = 0
for page in paginator.paginate(Bucket="backups-prod", Prefix="db/", PaginationConfig={"PageSize": 1000}):
    total += page["KeyCount"]            # objects AND rolled-up prefixes
    for obj in page.get("Contents", []):
        process(obj["Key"])
print(f"{total} entries listed")
```

**2. Count entries with `KeyCount`, never with `len(Contents)`.** The difference between the two is exactly the number of folders on that page.

**3. Use `StartAfter` when the job must be restartable.** AWS documents it as "where you want Amazon S3 to start listing from" and accepts "any key in the bucket", so a crashed job can resume from a key you persisted, without storing an opaque token that may not survive a client upgrade.

```bash
aws s3api list-objects-v2 --bucket backups-prod --prefix db/ --max-keys 1000 --start-after db/2026-11-09.tar
```

**4. Set `MaxKeys` below the ceiling when you need predictable pages.** A page size of 500 makes retries cheaper and keeps a single slow response from stalling the whole walk. Above 1,000 is silently clamped on real endpoints.

**5. Prove the cap on the endpoint you deploy against, not on the mock.** One run of the probe above answers what no test double can: whether this provider honours `MaxKeys`, whether prefixes share the budget, and what its token looks like.

**6. Verify a deletion or backup job against an independent count.** Log the entries processed and compare with the number the provider reports elsewhere: a job that lists 1,000 entries from a 30,000-object bucket and logs `done` is indistinguishable from success in every log you have.

## How S3 Explorer fits

Folder navigation in a desktop client is the same `delimiter` mechanism — each click is another LIST, and a folder holding more than 1,000 entries needs more than one. S3 Explorer's **per-request metrics** dashboard counts the API calls a session generated (`LIST`, `GET` and the rest), computed locally, so a browse that looks like one click can be read as the number of requests it really was. The **test connection** step reports how many buckets the credentials can see before a profile is saved, and **multiple connection profiles** let the same folder be opened on AWS and on a self-hosted endpoint from one window. [S3 Explorer](https://s3explorer.accessdevops.com) runs on Windows, macOS and Linux.

## Checklist

- [ ] Every list call loops on `IsTruncated`, or uses the SDK paginator.
- [ ] No code ends a loop by comparing `len(Contents)` with `MaxKeys`, or with 1,000.
- [ ] Entry counts use `KeyCount`, folders included.
- [ ] Nothing parses or reconstructs `NextContinuationToken`.
- [ ] Ordering assumptions are written down: UTF-8 binary, so numeric suffixes sort as text.
- [ ] `MaxKeys` is set explicitly and never above 1,000.
- [ ] At least one test runs against a real endpoint; the mock-only test is labelled as such.
- [ ] Cleanup and backup jobs log the entries they processed and compare against an independent count.

## Sources

- [Amazon S3 — ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html): "up to 1,000" per request; `MaxKeys` "will never contain more"; `KeyCount` "less than or equal to the MaxKeys field"; "Each rolled-up result counts as only one return against the MaxKeys value"; `NextContinuationToken` "obfuscated and is not a real key"; `StartAfter` starts listing after the given key.
- [Amazon S3 — Listing object keys programmatically](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html): a page of up to 1,000 keys with a truncation indicator; results "always returned in UTF-8 binary order"; list performance "not substantially affected by the total number of keys".
- [Amazon S3 — pricing](https://aws.amazon.com/s3/pricing/): LIST requests are billed with PUT, COPY and POST; console browsing "incur[s] charges for GET, LIST, and other requests that are made to facilitate browsing".
- [Cloudflare R2 — pricing](https://developers.cloudflare.com/r2/pricing/), page last updated 30 October 2026: Class A operations $4.50 per million, and `ListObjects` is listed as a Class A operation.
- Measured 11 November 2026 against SeaweedFS 4.50 and moto 5.2.5 with `boto3` 1.44.0; the probe is `scripts/list-pagination-probe.py` in this repository, and the bucket layout it builds is 3,547 objects, 2,501 of them under `flat/`.
