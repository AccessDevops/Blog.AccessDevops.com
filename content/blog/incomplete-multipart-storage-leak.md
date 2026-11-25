---
title: "The multipart uploads nobody finished, and what they cost"
description: "An interrupted upload keeps every part and loses the object. Measured: 16 MB invisible to any listing, and a lifecycle rule that can only wait a day."
date: 2026-11-25
author: "Clement Baranger"
tags: ["s3", "lifecycle", "cost"]
guide: incomplete-multipart-uploads
related: [multipart-5mb-floor-10000-parts, resume-interrupted-multipart-upload]
---

A nightly backup has failed at 85% for three weeks. The alert says network timeout, the retry says the same, and the bucket looks almost empty: the file list shows yesterday's dump and a gap. Nobody is worried, because nothing is missing that anyone can see. The invoices for that bucket have grown by 700 GB.

## The short version

- A multipart upload that is never completed keeps every part it already sent. The object does not exist, so nothing in a file listing shows it.
- Those parts are billed as storage — at the storage class the parts were uploaded with — for as long as they exist.
- Being invisible is the whole problem. Measured against a local S3 endpoint: 16,778,240 bytes of parts stored, and `ListObjectsV2` reporting zero keys.
- One bucket setting cleans them up automatically, `AbortIncompleteMultipartUpload`, and its unit is the day: no rule can delete a part the same afternoon.
- A 40 GB nightly dump that dies at 85% leaves 34 GB a night. Thirty nights of that is 1,020 GB, or $23.46 a month at $0.023/GB-month, and it keeps growing.

## What actually happens

A multipart upload is three calls around a loop: `CreateMultipartUpload` returns an upload ID, `UploadPart` sends numbered chunks, `CompleteMultipartUpload` joins them into an object. Everything the first two calls send is stored by the server immediately, as parts, keyed by the upload ID rather than by the object key. That is the design: it is what makes a resume possible and what lets a failing part be re-sent alone.

It is also why the parts are a second namespace. Until a completion arrives, they are not an object, cannot be read with `GetObject`, and do not appear in `ListObjectsV2`. AWS says so plainly in its [multipart upload overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html): "After you initiate a multipart upload, Amazon S3 retains all the parts until you either complete or stop the upload. Throughout its lifetime, you are billed for all storage, bandwidth, and requests for this multipart upload and its associated parts."

Two consequences follow from that sentence. There is no expiry — the same page states that after an upload is initiated "there is no expiry; you must explicitly complete or stop the multipart upload" — so nothing collects an abandoned upload except an abort or a lifecycle rule. And the parts carry a storage class: "These parts are billed according to the storage class specified when the parts are uploaded." An upload started against S3 Glacier Flexible Retrieval or Deep Archive is worse than it looks, because AWS bills those in-progress parts as Glacier staging storage at S3 Standard rates until the upload completes. An abandoned archive upload therefore sits on the bill at the most expensive rate in the account, not the cheapest.

![Line chart of storage held by incomplete multipart uploads from a 40 GB nightly dump failing at 85%: 34 GB a night accumulates to 1,020 GB and $23.46 a month after 30 nights, while an abort rule at one day holds the bill at 68 GB and $1.56, with ListObjectsV2 reporting zero keys throughout](/diagrams/incomplete-multipart-storage-leak.svg)

Finding them is a different API, and it is bucket-scoped. `ListMultipartUploads` returns what is in progress, one bucket at a time, 1,000 entries per response by default — the [API reference](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) calls 1,000 both the maximum and the default, and hands back `IsTruncated`, `NextKeyMarker` and `NextUploadIdMarker`. There is no account-wide call, so a fleet audit is a loop over buckets, and a loop that reads the first page answers for the first 1,000 uploads only.

## Where it bites

I ran the two failure modes against SeaweedFS 4.50 (`weed server -s3`) with `boto3` 1.44.11, on a bucket that had nothing else in it:

```bash
python3 scripts/incomplete-mpu-probe.py start http://127.0.0.1:18337
```

| Check | Result |
|---|---|
| `ListObjectsV2` after three 5 MiB parts | `KeyCount=0` |
| `ListMultipartUploads` | 1 upload, key `backups/postgres/db-2026-11-25.tar`, `Initiated` timestamp |
| `ListParts` | 3 parts of 5,242,880 bytes: 15,728,640 bytes |
| Complete after a 1 MiB first part | `400 EntityTooSmall` — "Your proposed upload is smaller than the minimum allowed object size." |
| After that refusal | a second upload holding 1,049,600 bytes, still no object |
| Three uploads in progress, `MaxUploads=1` | `IsTruncated=True`, `NextKeyMarker='backups/job-1.tar'` |
| Lifecycle rule `DaysAfterInitiation=1` written and read back | stored; nothing deleted in the same second |
| Both uploads aborted | 0 uploads, 0 bytes |

**The refused completion is the one people forget.** The upload in the fourth row failed at the end, like the [5 MiB part floor](/blog/multipart-5mb-floor-10000-parts) case: every `UploadPart` returned `200`, then the completion was rejected, and the client's error handling moved on. The parts stayed, because a failed completion is not an abort. Two different leaks — an abandoned upload and a rejected one — look identical from `ListObjectsV2` and identical from the invoice.

**Attribution is thin on compatible servers.** SeaweedFS 4.50 returned no `Initiator` and no `StorageClass` for either upload, so nothing in the listing says which principal started it or what it is being billed at. AWS returns both. If the audit is meant to find the *job* rather than the bytes, the cheap way is the `CreateMultipartUpload` data event in CloudTrail, or the server access log line for that request; the bucket listing alone will not name anyone.

**The lifecycle rule cannot be hurried.** `AbortIncompleteMultipartUpload` takes a `DaysAfterInitiation` value — the [rule definition](https://docs.aws.amazon.com/AmazonS3/latest/API/API_LifecycleRule.html) describes it as the days to wait "before permanently removing all parts of the upload" — and days are the unit. The rule applies to uploads that already exist as well as new ones, and the documented example uses 7. Rewriting it to 1 does not act on an upload created a minute ago, so a rule bounds the leak, it does not close it: budget one to two nights of parts as the standing residue.

**It blocks bucket deletion.** On directory buckets, AWS states that a bucket cannot be deleted while multipart uploads are in progress; the same heuristics apply to a stack teardown anywhere. A test environment that "will not delete its bucket" is usually holding orphaned parts.

**The bill is not linear in data, it is linear in time.** 34 GB a night for a month is 1,020 GB, and a month later it is 2,040 GB. The parts are priced at $0.023/GB-month for the first 50 TB in us-east-1, from the AWS price list published 2026-11-21, so the first month of that one failing job costs $23.46 and the next month adds another $23.46 on top. The upload that produced them is visible in a log nobody reads.

## Doing it right

**1. Audit every bucket, and page properly.** Two markers, not one, and a real `Prefix` when the bucket is large.

```python
def incomplete_uploads(s3):
    for b in s3.list_buckets()["Buckets"]:
        name = b["Name"]
        kw = {"Bucket": name}
        while True:
            page = s3.list_multipart_uploads(**kw)
            for u in page.get("Uploads", []):
                yield name, u
            if not page.get("IsTruncated"):
                break
            kw["KeyMarker"] = page["NextKeyMarker"]
            kw["UploadIdMarker"] = page["NextUploadIdMarker"]
```

**2. Sum the bytes before deciding anything.** The count of uploads says nothing about the size of the problem; the parts do.

```python
def orphaned_bytes(s3, bucket, upload):
    total = 0
    kw = {"Bucket": bucket, "Key": upload["Key"], "UploadId": upload["UploadId"]}
    while True:
        page = s3.list_parts(**kw)
        total += sum(p["Size"] for p in page.get("Parts", []))
        if not page.get("IsTruncated"):
            return total
        kw["PartNumberMarker"] = page["NextPartNumberMarker"]
```

**3. Put a lifecycle rule on every bucket as a default, not as a remediation.** The rule lives with the bucket, so a bucket created by a template that lacks it is born leaking.

```bash
aws s3api put-bucket-lifecycle-configuration --bucket backups-prod \
  --lifecycle-configuration '{"Rules":[{"ID":"abort-incomplete-multipart",
  "Status":"Enabled","Filter":{"Prefix":""},
  "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":2}}]}'
```

Two days rather than one when nightly jobs are resumable: a 24-hour restart window is real, and the [resume path for an interrupted upload](/blog/resume-interrupted-multipart-upload) depends on the parts still being there.

**4. Abort in a `finally`, and abort what the rule cannot reach yet.** A job that gives up knows its own upload ID and should not leave the decision to a lifecycle pass a day later. `s3:AbortMultipartUpload` is the permission it needs, and it is usually missing from the role that only had `PutObject`.

**5. Alarm on age, not on count.** The signal that matters is the oldest `Initiated` timestamp in the listing, not how many uploads exist. A bucket with 300 five-minute uploads is healthy; a bucket with one three-day-old upload is a job that will never finish.

**6. Prove the measurement on the endpoint you run.** The probe in this repository leaves the orphans behind, prints the byte total, and aborts them afterwards, so the same command answers whether your provider even reports parts.

```bash
python3 scripts/incomplete-mpu-probe.py start https://s3.eu-west-3.amazonaws.com
python3 scripts/incomplete-mpu-probe.py abort https://s3.eu-west-3.amazonaws.com
```

## How S3 Explorer fits

Finding the leak is a listing problem: which buckets, how many uploads, how large. S3 Explorer's **bucket list and folder navigation** open a bucket without a CLI round trip, its **per-request metrics** dashboard counts the `LIST` calls a session generated — the number that shows whether an audit loop is paging correctly or re-reading the same page — and **test connection** reports how many buckets the credentials actually see before a profile is saved, which is also the fastest way to learn that an audit key can see four buckets and not the twenty you assumed. The provider picker's 25 presets let AWS and a self-hosted endpoint be compared in one window. The cleanup procedure itself, with the lifecycle rule to copy, is written up in [the guide to finding and deleting incomplete multipart uploads](https://s3explorer.accessdevops.com/guides/incomplete-multipart-uploads/?utm_source=blog&utm_medium=in_article&utm_campaign=incomplete-multipart-storage-leak).

## Checklist

- [ ] Every bucket has an `AbortIncompleteMultipartUpload` rule, and the day count is documented next to the job that expects it.
- [ ] The audit loop follows `NextKeyMarker` and `NextUploadIdMarker` until `IsTruncated` is false.
- [ ] The audit reports total *bytes* of orphaned parts, not a count of uploads.
- [ ] Every multipart code path has `abort_multipart_upload` in a `finally`.
- [ ] The role that uploads also carries `s3:AbortMultipartUpload` and `s3:ListMultipartUploadParts`.
- [ ] A failure in `CompleteMultipartUpload` is treated as a leak, not as a handled error.
- [ ] An alarm fires on the oldest `Initiated` timestamp per bucket.
- [ ] New buckets get the rule from the template, not from a runbook.

## Sources

- [Amazon S3 — multipart upload overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html): parts retained until complete or stop, "you are billed for all storage, bandwidth, and requests", billing at the storage class of the upload, Glacier staging billed at S3 Standard rates, "there is no expiry".
- [Configuring a lifecycle rule to delete incomplete multipart uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html): the `AbortIncompleteMultipartUpload` action, its effect on existing and future uploads, the 7-day example, no early delete charges.
- [`LifecycleRule`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_LifecycleRule.html): `AbortIncompleteMultipartUpload` described as "the days since the initiation of an incomplete multipart upload that Amazon S3 will wait before permanently removing all parts of the upload".
- [`ListMultipartUploads`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html): 1,000 as both maximum and default, `IsTruncated`, `NextKeyMarker`, `NextUploadIdMarker`, the directory-bucket deletion restriction.
- [Amazon S3 price list, us-east-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json), publication date 2026-11-21: $0.023 per GB-month for the first 50 TB of S3 Standard storage.
- Measured 25 November 2026 with `boto3` 1.44.11 against SeaweedFS 4.50 (`weed server -dir=/data -s3 -s3.port=8333`, gateway on `127.0.0.1:18337`), using `scripts/incomplete-mpu-probe.py` in this repository; the diagram is generated by `scripts/leak-diagram.py`.
