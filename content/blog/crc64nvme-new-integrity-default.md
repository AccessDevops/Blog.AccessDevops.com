---
title: "CRC64NVME is now the S3 default, your SDK sends CRC32"
description: "S3 stores a CRC64NVME checksum on every new object, while the CLI and the SDKs default to different algorithms. Measured on a live endpoint."
date: 2026-11-09
author: "Clement Baranger"
tags: ["s3", "integrity", "api"]
guide: s3-error-codes
related: [multipart-5mb-floor-10000-parts, presigned-post-enforce-size-content-type]
---

A nightly backup starts answering `400 BadDigest`, and the message is about Content-MD5. No MD5 was ever sent: the SDK sends a base64 CRC now. Nothing in the repository changed between the last good run and the first bad one — a default did, and it decides which checksum travels with the object.

## The short version

- Since 1 December 2024 S3 stores a CRC-based checksum on every new object, even when the client sends none; the algorithm it picks for itself is CRC64NVME.
- The algorithm the client sends is a separate decision, and the clients disagree: AWS CLI v2 defaults to CRC64NVME, while boto3, Go, Java and JavaScript default to CRC32. One bucket can hold both without anyone choosing.
- Reading the value back is opt-in: without `x-amz-checksum-mode: ENABLED` a `HEAD` returns no checksum at all, on an object that has one.
- A mismatch is `400 BadDigest`, whose documented text talks about Content-MD5 whatever you sent, and the SDK re-sends the whole request first — six attempts by default on one small object.
- The cost is CPU, not storage. A pure-Python CRC64NVME runs at 3.8 MiB/s on this machine against 5.86 GiB/s for the C library: 7.5 hours instead of 18 seconds for 100 GB.

## What actually happens

The checksum is computed by the client, before the first byte moves. It travels as a header named after the algorithm — `x-amz-checksum-crc64nvme`, `x-amz-checksum-crc32` — with the 8-byte or 4-byte value base64-encoded, which is why a CRC64 looks like a twelve-character string such as `01qn/OUzLVc=`. As an `x-amz-` header on a signed request it joins `SignedHeaders`, so a middlebox that rewrites it breaks the signature, not the checksum.

On arrival S3 recomputes the value over the bytes it received and compares. Equal: the object is stored and the checksum goes into its metadata, re-readable months later. Not equal: nothing is stored.

Since 1 December 2024 that happens whether or not your code participates: the [AWS announcement](https://aws.amazon.com/blogs/aws/introducing-default-data-integrity-protections-for-new-objects-in-amazon-s3/) says S3 computes a CRC and stores it for new objects even when the client sends nothing, and the [user guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html) adds that when neither you nor the SDK chooses an algorithm, S3 uses CRC64NVME. That page lists ten accepted algorithms, five [added on 23 April 2026](https://aws.amazon.com/about-aws/whats-new/2026/04/s3-five-additional-checksum-algorithms/).

![Four steps of a signed upload — the client computes the CRC, Signature V4 covers the header, the server recomputes and compares before storing, and a read returns the value only when checksum mode is enabled — with a bottom band showing that the CLI sends CRC64NVME, the SDKs send CRC32, and a client that sends nothing gets CRC64NVME stored for it](/diagrams/crc64nvme-new-integrity-default.svg)

Whether the stored value can verify a file depends on the checksum type. For a multipart upload it is either `COMPOSITE` — the checksum of the concatenated part checksums, exactly like a multipart ETag — or `FULL_OBJECT`, computed as if the object were one stream. Only the CRC family can linearise, so only CRC32, CRC32C and CRC64NVME support `FULL_OBJECT`, and a composite value cannot be compared with a CRC computed over the whole file.

## Where it bites

I ran the cases against SeaweedFS 4.50 (`weed server -s3`, a container on this machine) with `boto3` 1.43.126. The object was 44,000 bytes, its CRC64NVME `01qn/OUzLVc=`.

| Case | What the endpoint did |
|---|---|
| `put_object` with no checksum argument | SDK sent `x-amz-checksum-crc32` on its own; `200`, CRC32 echoed back |
| Correct CRC64NVME | `200`, `x-amz-checksum-crc64nvme: 01qn/OUzLVc=` in the response |
| Wrong CRC64NVME | `400 BadDigest` — "The Content-MD5 you specified did not match what we received." |
| `head_object` without checksum mode | no checksum field in the response |
| Multipart, CRC64NVME, `FULL_OBJECT` | completed, checksum equal to the CRC64 of the concatenated parts |
| Multipart, CRC64NVME, `COMPOSITE` | `400 InvalidRequest` — "Invalid Request" |

```bash
python3 scripts/checksum-probe.py probe http://127.0.0.1:8333 demo demosecret123
```

**The error names an algorithm you did not use.** `BadDigest` is the documented code, and the [error catalogue](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Error.html) gives it one description: "The Content-MD5 you specified did not match what we received." SeaweedFS returned that sentence verbatim for a CRC64NVME mismatch, so a reader who trusts the text hunts a `Content-MD5` header nobody has sent since 2024. Catch on the code instead.

**The retry re-sends the object.** With the default retry configuration, botocore made six attempts at the 44,000-byte body before raising. A mismatch means the arriving bytes are not the sent bytes, so re-sending identical content is unlikely to help — but it happens anyway, and every attempt is a full payload. On a 100 MiB part that is 600 MiB on the wire, about 48 seconds per failed part at 100 Mbit/s: the same amplification as [a multipart upload restarted instead of resumed](/blog/multipart-5mb-floor-10000-parts).

**The constant is easy to get wrong by one nibble.** CRC-64/NVME is published as polynomial `0xAD93D23594C935A9`, init all-ones, xorout all-ones, reflected in and out. Fed least-significant-bit first, the constant that reproduces the published vectors is `0x9A6C9329AC4BC9B5`. Bit-reversing the published polynomial by hand gives `0x95AC9329AC4BC9B5`, which yields `0x3558e8e979f60d7e` for `123456789` — a well-formed 8-byte checksum no endpoint will agree with, and nothing fails locally. Verify against the vectors first:

```bash
python3 scripts/checksum-probe.py crc
```

```text
input "123456789"    0xae8b14860a799888   rosUhgp5mIg=
input "Hello World!" 0x02e51cc85efce1a5   AuUcyF784aU=
input ""             0x0000000000000000   AAAAAAAAAAA=
```

**Providers implement a subset, and the failure is not always a checksum error.** Cloudflare R2 accepts CRC64NVME for `FULL_OBJECT` only and CRC32 for `COMPOSITE` only, [per its compatibility table](https://developers.cloudflare.com/r2/api/s3/api/); CRC64NVME arrived for single and multipart objects on [3 July 2025](https://developers.cloudflare.com/r2/platform/release-notes/). Before that, the CLI's move broke uploads against R2 with `Header 'x-amz-checksum-algorithm' with value 'CRC32' not implemented`. A header error surfaces before any data is validated, so a log grep for `BadDigest` finds nothing.

**Silence is the worst outcome.** An object stored with a CRC32 while the reader expects CRC64NVME is not an error anywhere: `HEAD` returns `ChecksumCRC32`, the script looks for `ChecksumCRC64NVME`, finds nothing, and passes.

## Doing it right

**1. Choose the algorithm in the request, not in a comment.** Pass it explicitly so the version of the SDK stops deciding for you.

```python
import boto3, base64
from botocore.config import Config

s3 = boto3.client("s3", config=Config(request_checksum_calculation="when_supported"))
s3.put_object(Bucket="backups-prod", Key="db/2026-11-09.tar", Body=body,
              ChecksumAlgorithm="CRC64NVME", ChecksumCRC64NVME="01qn/OUzLVc=")
```

Telling the SDK to stop calculating at all is the other option — `when_required`, or `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` — right only when an endpoint rejects the header. Turning it off does not turn off what S3 stores.

**2. Compute it once, on the way past.** The digest has to exist before the upload to be compared at all; a second read of the file afterwards measures the local copy twice and the network once.

```python
from awscrt import checksums
import base64

with open("/backups/db-2026-11-09.tar", "rb") as f:
    digest = base64.b64encode(
        checksums.crc64nvme(f.read()).to_bytes(8, "big")).decode()
```

`awscrt.checksums` ships with the AWS CRT and Go's `crc64` has `crc64nvme`; a Python loop is 1,500× slower, and the fast path is already in the SDK you installed.

**3. Ask for `FULL_OBJECT` when you intend to compare whole files.** On `CreateMultipartUpload`, set `ChecksumAlgorithm="CRC64NVME"` with `ChecksumType="FULL_OBJECT"`. A `COMPOSITE` value answers a different question — whether the parts arrived intact — and cannot be compared to a CRC of the local file. Two 5 MiB parts of `\x01` and `\x02` returned `XwQeSvWLj+8=`, the CRC64 of the concatenation, not of the part checksums.

**4. Read the value back deliberately.** `head_object(..., ChecksumMode="ENABLED")` or `get_object` with the same argument; without it the field is absent. On download, compare the returned base64 with your own value, or let the SDK do it via `response_checksum_validation`.

**5. Prove it on the endpoint you deploy against.** The probe creates a bucket called `crc-probe` and runs the table above in one command:

```bash
python3 scripts/checksum-probe.py probe https://<account>.r2.cloudflarestorage.com <key> <secret>
```

A provider that answers `200` while storing nothing is what the table is for. The same principle governs [presigned POST policies that cap size and content type](/blog/presigned-post-enforce-size-content-type): the server enforces what the request declares, so the declaration must be right before the upload starts.

## How S3 Explorer fits

Which checksum an object carries, and which one the endpoint will return, differ per provider, so the useful check is a read against the real endpoint. S3 Explorer's **provider picker** holds 25 presets across Cloud, Specialist, Self-hosted and Enterprise plus a Custom tile, so an R2 bucket and an S3 bucket open from the same window. Its **Metadata** tab shows the headers the server returned, which is where a stored checksum appears when the endpoint sends one, and **test connection** reports how many buckets the credentials can see. [S3 Explorer](https://s3explorer.accessdevops.com) runs on Windows, macOS and Linux.

## Checklist

- [ ] Every upload path names its checksum algorithm, or documents the SDK default it relies on.
- [ ] The checksum is computed before the upload and compared with the value the server returns.
- [ ] Multipart paths that need whole-file verification declare `FULL_OBJECT`, and never compare a composite value to a local CRC.
- [ ] Downloads enable checksum mode, or the SDK validates the response.
- [ ] The reader accepts whichever algorithm the object carries, and a missing checksum fails the job.
- [ ] The CRC implementation is tested against the three published vectors, not only against itself.
- [ ] `BadDigest` is capped by the retry policy, not retried as a network error.

## Sources

- [AWS — default data integrity protections](https://aws.amazon.com/blogs/aws/introducing-default-data-integrity-protections-for-new-objects-in-amazon-s3/), 1 December 2024: S3 stores a CRC on new objects even without one from the client; `x-amz-checksum-type` with `FULL_OBJECT` or `COMPOSITE`; the `AuUcyF784aU=` example for `Hello World!`.
- [AWS — checking object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html): ten algorithms, `BadDigest` on a mismatch, `FULL_OBJECT` limited to CRC algorithms, CRC64NVME when nothing is specified, and REST calls using `x-amz-checksum-<algorithm>`.
- [AWS SDK data integrity protections](https://docs.aws.amazon.com/sdkref/latest/guide/feature-dataintegrity.html): per-SDK defaults (CLI v2 CRC64NVME; boto3, Go, Java, JavaScript CRC32) and the `request_checksum_calculation` / `response_checksum_validation` settings.
- [S3 error catalogue](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Error.html): `BadDigest`, 400, "The Content-MD5 you specified did not match what we received."
- [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html) and [HeadObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html): "To retrieve the checksum, this mode must be enabled".
- [R2 S3 compatibility](https://developers.cloudflare.com/r2/api/s3/api/): CRC64NVME `FULL_OBJECT` only, CRC32 `COMPOSITE` only; [release notes](https://developers.cloudflare.com/r2/platform/release-notes/), 3 July 2025.
- Measured 9 November 2026 against SeaweedFS 4.50 with `boto3` 1.43.126 and `awscrt`; the probe is `scripts/checksum-probe.py`.
