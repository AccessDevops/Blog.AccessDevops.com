---
title: "ETag is not MD5: verifying integrity on multipart objects"
description: "An ETag identifies the upload, not the bytes: the same file sent in two parts and in four parts gets two different values. What to compare instead."
date: 2026-11-18
author: "Clement Baranger"
tags: ["s3", "uploads", "integrity"]
guide: incomplete-multipart-uploads
related: [crc64nvme-new-integrity-default, resume-interrupted-multipart-upload]
---

A nightly job downloads every object the release train published, hashes the file, compares the hash with the ETag that `HeadObject` returned, and reports a mismatch on all of them. Nothing is corrupt. The upload was split into parts, and a multipart ETag is not the MD5 of the file — it is the MD5 of the part MD5s, with the number of parts glued on the end. The check was written against the one upload path that produces an MD5 and then pointed at the path that does not.

## The short version

- The ETag names one upload of an object. It is not a checksum of the bytes, and two uploads of the same file legitimately carry two different ETags.
- A single `PUT` of a plaintext or SSE-S3 object returns the file's MD5. That is the only common case where an ETag can verify a download.
- Any multipart upload returns the MD5 of the concatenated binary part MD5s, then a dash and the part count: `…-2` for two parts, `…-4` for four. Measured below on one 20 MiB file.
- The console uploads anything over 16 MB as multipart; SSE-C and SSE-KMS break the MD5 relationship even for a single part.
- An integrity gate that treats the ETag as the file's checksum either re-sends healthy data or gets disabled after the first false alarm — and then real corruption passes. Re-sending 1 TB at 100 Mbit/s takes 22 hours.

## What actually happens

The rule is documented rather than hidden. The S3 API reference says the ETag "may or may not be an MD5 digest of the object data", then lists when it is: `PutObject`, `PostObject`, `CopyObject` or the console, encrypted with SSE-S3 or plaintext. Encrypted with SSE-C or SSE-KMS, the ETag is "not an MD5 digest of their object data". And: "If an object is created by either the Multipart Upload or Part Copy operation, the ETag is not an MD5 digest, regardless of the method of encryption."

The same page describes the multipart value precisely: S3 calculates the MD5 of each part as it arrives, "concatenates the bytes for the MD5 digests together and then calculates the MD5 digest of these concatenated values", and adds "a dash with the total number of parts to the end". As a formula:

```
ETag = hex(MD5( MD5(p1) ‖ MD5(p2) ‖ … ‖ MD5(pn) )) + "-" + n
```

What the formula depends on is the **part layout**. Identical bytes split 2 × 10 MiB and 4 × 5 MiB produce two different ETags, because a different set of part digests is concatenated. The object is the same; the identifier of the upload is not. The ETag answers "is this the upload I completed", not "are these the bytes I sent".

![One 20 MiB file uploaded three ways: a single PUT returns its MD5, a two-part and a four-part multipart upload of identical bytes return a hash of the part hashes with the part count appended, and a bottom band gives the composite rule plus the measured case where a server-side copy kept the composite ETag](/diagrams/etag-is-not-md5-on-multipart.svg)

The value comes back quoted — `"4ffc00e6…"`, dash and count inside the quotes — from `HeadObject`, from `ListObjectsV2`, from the console. Strip the quotes on one side and not the other and every comparison fails on objects that are perfectly fine. It is the cheapest way to write this bug.

Other providers make the same header mean different things. Cloudflare R2 documents the identical construction — parts `bce6bf66…` and `8165449…` complete to `f77dc0eecdebcd774a2a22cb393ad2ff-2` — but only adopted MD5-based multipart ETags on 21 June 2023, so older objects do not match today's recipe. Google Cloud Storage documents the opposite: "Composite objects do not have an MD5 hash metadata field", and a composite "ETag value … is not based on an MD5 hash". MinIO's API docs call the ETag field the "MD5 checksum of the object" and never state the multipart rule; the formula survives only in minio-go's source. Backblaze's S3 reference shows an ETag in every example and defines none. One protocol, five promises about the same header.

## Where it bites

I uploaded the same 20 MiB payload four ways against SeaweedFS 4.50 (`weed server -s3`, a container on this machine at `http://127.0.0.1:18333`) with `boto3` 1.44.5. The file's own MD5 is `4ffc00e6e0d625f936b806a86a392c98`.

| Upload path | ETag returned | Equal to the file MD5? |
|---|---|---|
| One `PUT`, 20 MiB | `"4ffc00e6e0d625f936b806a86a392c98"` | yes |
| Multipart, 2 × 10 MiB | `"fbad3182280f8de3b9cb78094f2fb990-2"` | no |
| Multipart, 4 × 5 MiB | `"c87fa7c13b8a90030bbaa9fe45870eb2-4"` | no |
| `CopyObject` of the 4-part object | `"c87fa7c13b8a90030bbaa9fe45870eb2-4"` | no |

```bash
python3 scripts/etag-probe.py http://127.0.0.1:18333
```

**The composite formula is exact.** Recomputing `hex(MD5(MD5(p1) ‖ … ‖ MD5(pn)))-n` from the local bytes reproduced both multipart ETags character for character. Nothing is lossy or provider-specific about the construction, which is why the failure is so quiet: the check is *wrong*, not buggy, and it fails the same way every night.

**The copy row is the surprise.** AWS documents a plaintext object created by `CopyObject` as having an MD5 ETag. This endpoint kept the source's composite value instead, so the same 20 MiB of bytes ended up with `…-4` attached under a new key. A pipeline that copies an object — to another prefix, bucket or SSE mode — then verifies the copy against a stored ETag cannot assume either that the ETag survives or that it changes in the documented way.

**A one-part multipart upload is still suffixed.** The dash is not proof that several parts were used: completing a multipart upload with a single part stores `"64a3b22c…-1"`, measured while probing [the 5 MiB floor and the 10,000-part ceiling](/blog/multipart-5mb-floor-10000-parts). "No dash means single part" holds; "one part means MD5" does not.

**The fallback is not always there.** The same probe asked for `ChecksumCRC32C`, `ChecksumCRC32` and `ChecksumCRC64NVME` on every `HeadObject` and got `null` in all four cases: this endpoint stores no checksum header at all. On AWS those fields are the real answer to "verify these bytes", but a path that silently degrades to the ETag when a checksum is missing starts comparing the wrong thing on exactly the providers that return neither — the same trap as [the checksum defaults that disagree between CLI and SDK](/blog/crc64nvme-new-integrity-default), one layer down.

**The cost is in the retries.** A false mismatch in a release gate does not stay a warning. Someone adds a re-upload and the job sends every object twice; 1 TB at 100 Mbit/s is 22 hours, paid again on each run. The alternative ending is worse: the check gets commented out, and nothing notices a truncated object — an upload resumed from a part list that lied, the case measured in [resuming a multipart upload you never meant to abandon](/blog/resume-interrupted-multipart-upload).

## Doing it right

**1. Decide what the ETag is asked to prove.** "Are the stored bytes the bytes I sent" — the ETag is the wrong instrument above one part. "Is this the object I completed two minutes ago" — it is exactly right.

**2. Compare MD5 only with no dash and no SSE-KMS/SSE-C.** That is the documented subset, and it is small.

```python
head = s3.head_object(Bucket=b, Key=k)
etag = head["ETag"].strip('"')
kms_or_customer_key = "SSEKMSKeyId" in head or "SSECustomerAlgorithm" in head
if "-" not in etag and not kms_or_customer_key:
    assert etag == hashlib.md5(local_bytes).hexdigest()
```

**3. Recompute the composite when you know the chunk size.** The part layout is not recoverable after completion — `ListParts` answers only for an in-progress upload — so the check needs the chunk size the writer used, which belongs in the job config next to the file size.

```python
def composite_etag(path: str, chunk: int) -> str:
    md5s, n = b"", 0
    with open(path, "rb") as f:
        while block := f.read(chunk):
            md5s += hashlib.md5(block).digest()
            n += 1
    return f'"{hashlib.md5(md5s).hexdigest()}-{n}"'
```

**4. Prefer a full-object checksum, and send it yourself.** The CRC family linearises, so `FULL_OBJECT` composites exist for CRC32, CRC32C and CRC64NVME; MD5 cannot be a full-object checksum on a multipart upload. Send `x-amz-checksum-crc32c`, read it back with `ChecksumMode="ENABLED"`, and keep your own digest in metadata as the second opinion no provider can redefine.

**5. Prove the check on the target endpoint.** Upload one 6 MiB file once whole and once as two 3 MiB parts, and confirm the ETags differ. Two calls answer what no documentation can: whether this implementation follows the composite rule, and whether it returns checksums at all.

## How S3 Explorer fits

Reading an ETag is a browsing problem before it is a code problem: the value depends on the upload path and the provider, so the useful move is to look at it on the object being argued about. S3 Explorer shows the ETag as the server returned it in each object's **Metadata** tab, beside the **Versions** tab, and its **provider picker** holds 25 presets across Cloud, Specialist, Self-hosted and Enterprise plus a Custom tile, so the same key opens on AWS and on a self-hosted server from one window. The **test connection** step reports how many buckets the credentials actually see before a profile is saved. [S3 Explorer](https://s3explorer.accessdevops.com/guides/incomplete-multipart-uploads/?utm_source=blog&utm_medium=in_article&utm_campaign=etag-is-not-md5-on-multipart) runs on Windows, macOS and Linux.

## Checklist

- [ ] Every integrity check states which upload path it assumes, in writing.
- [ ] No code compares an ETag containing a dash with an MD5, throwaway scripts included.
- [ ] Quotes are stripped the same way on both sides of every comparison.
- [ ] SSE-KMS and SSE-C objects are excluded from MD5 comparison by name, not by accident.
- [ ] The writer's chunk size is recorded, so a composite ETag can be recomputed a month later.
- [ ] Checksums are requested with `ChecksumMode=ENABLED`, and a missing checksum is a failure.
- [ ] The probe has been run against the production endpoint, and its result is recorded.

## Sources

- [Amazon S3 — Object (ETag)](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Object.html): "may or may not be an MD5 digest"; the SSE cases, the multipart case, the console's 16 MB threshold.
- [Amazon S3 — Content-MD5 and the ETag](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html): per-part MD5s concatenated, MD5 of the concatenation, dash and part count.
- [Cloudflare R2 — Upload objects](https://developers.cloudflare.com/r2/objects/upload-objects/): the `-N` format and a two-part example; [release notes, 21 June 2023](https://developers.cloudflare.com/r2/platform/release-notes/): "Multipart ETags are now MD5 hashes."
- [Google Cloud Storage — Composite objects](https://docs.cloud.google.com/storage/docs/composite-objects): no MD5 field, and an ETag that is not MD5-based.
- [Backblaze B2 — b2_get_file_info](https://www.backblaze.com/apidocs/b2-get-file-info): `contentMd5` null for large files; [S3 Head Object](https://www.backblaze.com/apidocs/s3-head-object) defines no ETag.
- [Wasabi — Operations on objects](https://docs.wasabi.com/apidocs/operations-on-objects): a composed object carries the hash of its source MD5s.
- [MinIO Go SDK — StatObject](https://docs.min.io/aistor/developers/sdk/go/api/): ETag as "MD5 checksum of the object"; the multipart formula lives in [minio-go's source](https://github.com/minio/minio-go/blob/master/api-datatypes.go).
- Measured 18 November 2026 against SeaweedFS 4.50 (docker image `chrislusf/seaweedfs:latest`) with `boto3` 1.44.5, by `scripts/etag-probe.py`.
