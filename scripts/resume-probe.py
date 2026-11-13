#!/usr/bin/env python3
"""Resume probe: what survives a crashed multipart upload, and what an upload
ID does when you come back to it.

    python3 scripts/resume-probe.py http://127.0.0.1:18334

Needs a running S3-compatible endpoint and `boto3`. Creates bucket
`resume-probe`, uploads 2 x 5 MiB + 1 KiB parts, and prints the exact
error strings an endpoint returns for each way a resume can go wrong.

Ran on 2026-11-13 against SeaweedFS 4.50 (`weed server -s3`, docker image
chrislusf/seaweedfs:latest) and moto 5.2.5, with boto3 1.44.2.
"""
import hashlib
import sys

import boto3
import botocore
from botocore.config import Config

MIB = 1024 * 1024
BUCKET = "resume-probe"


def client(endpoint):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="probe",
        aws_secret_access_key="probe",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 1}),
    )


def err(e):
    """The exact code and message the endpoint sent, unedited."""
    r = getattr(e, "response", {}).get("Error", {})
    status = getattr(e, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
    return f"{status} {r.get('Code')}: {r.get('Message')}"


def blob(seed, size):
    return (hashlib.sha256(seed.encode()).digest() * (size // 32 + 2))[:size]


def main(endpoint):
    s3 = client(endpoint)
    try:
        s3.create_bucket(Bucket=BUCKET)
    except botocore.exceptions.ClientError:
        pass

    key = "db-2026-11-13.tar"
    parts = {1: blob("one", 5 * MIB), 2: blob("two", 5 * MIB), 3: blob("three", 1024)}

    # --- 1. initiate, upload two parts, then "crash" (lose every ETag) ---
    uid = s3.create_multipart_upload(Bucket=BUCKET, Key=key)["UploadId"]
    print(f"upload id: {uid}")
    for n in (1, 2):
        s3.upload_part(Bucket=BUCKET, Key=key, UploadId=uid, PartNumber=n, Body=parts[n])
    print("parts 1 and 2 sent, local state discarded")

    # --- 2. can the restart find the upload without a state file? ---
    found = [
        u["UploadId"]
        for u in s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads", [])
        if u["Key"] == key
    ]
    print(f"list_multipart_uploads finds {len(found)} upload(s) for {key}: {uid in found}")

    # --- 3. and the parts? ListParts is the resume path ---
    lp = s3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid)
    print(f"list_parts: {len(lp.get('Parts', []))} parts, IsTruncated={lp.get('IsTruncated')}")
    for p in lp.get("Parts", []):
        print(f"  part {p['PartNumber']}  {p['Size']} bytes  ETag {p['ETag']}")
    resume = [{"PartNumber": p["PartNumber"], "ETag": p["ETag"]} for p in lp["Parts"]]

    # --- 4. MaxParts truncation ---
    one = s3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid, MaxParts=1)
    print(
        f"max_parts=1 -> {len(one.get('Parts', []))} part, "
        f"IsTruncated={one.get('IsTruncated')}, "
        f"NextPartNumberMarker={one.get('NextPartNumberMarker')}"
    )

    # --- 5. re-uploading a part number that already exists ---
    before = {p["PartNumber"]: p["ETag"] for p in lp["Parts"]}
    redo = s3.upload_part(Bucket=BUCKET, Key=key, UploadId=uid, PartNumber=2, Body=blob("two-bis", 5 * MIB))
    after = {p["PartNumber"]: p["ETag"] for p in s3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid)["Parts"]}
    print(f"re-upload part 2 accepted: {redo['ETag'] != before[2]}, ETag replaced: {after[2] != before[2]}")
    print(f"part count after re-upload: {len(after)}")
    resume = [{"PartNumber": n, "ETag": e} for n, e in sorted(after.items())]

    # --- 5b. which bytes actually land, the stale ETag or the new part? ---
    # The re-upload returned its own ETag; ListParts still shows the old one.
    # Complete with the OLD ETag, then hash the object to see what was stored.
    print(f"upload_part returned ETag {redo['ETag']}, list_parts still shows {after[2]}")

    # --- 6. resume: send only the missing part, complete from ListParts ---
    s3.upload_part(Bucket=BUCKET, Key=key, UploadId=uid, PartNumber=3, Body=parts[3])
    resume.append({"PartNumber": 3, "ETag": s3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid,
                                                          PartNumberMarker=2)["Parts"][0]["ETag"]})
    done = s3.complete_multipart_upload(
        Bucket=BUCKET, Key=key, UploadId=uid, MultipartUpload={"Parts": resume}
    )
    head = s3.head_object(Bucket=BUCKET, Key=key)
    print(f"resumed and completed: {head['ContentLength']} bytes, ETag {head['ETag']}")
    stored = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    old = hashlib.sha256(parts[1] + parts[2] + parts[3]).hexdigest()
    new = hashlib.sha256(parts[1] + blob("two-bis", 5 * MIB) + parts[3]).hexdigest()
    got = hashlib.sha256(stored).hexdigest()
    which = "the re-uploaded part 2" if got == new else "the original part 2" if got == old else "neither"
    print(f"stored object is {len(stored)} bytes of {which}: {got[:16]}")

    # --- 7. completing a finished upload id ---
    try:
        s3.complete_multipart_upload(Bucket=BUCKET, Key=key, UploadId=uid,
                                     MultipartUpload={"Parts": resume})
        print("complete after complete: accepted (no error)")
    except botocore.exceptions.ClientError as e:
        print(f"complete after complete -> {err(e)}")

    # --- 8. a wrong ETag in the part list ---
    uid2 = s3.create_multipart_upload(Bucket=BUCKET, Key="wrong-etag.tar")["UploadId"]
    p1 = s3.upload_part(Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2, PartNumber=1, Body=parts[1])
    try:
        s3.complete_multipart_upload(
            Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2,
            MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": '"' + "0" * 32 + '"'}]},
        )
        print("wrong ETag: accepted (no error)")
    except botocore.exceptions.ClientError as e:
        print(f"wrong ETag -> {err(e)}")

    # --- 9. parts out of order ---
    try:
        s3.complete_multipart_upload(
            Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2,
            MultipartUpload={"Parts": [{"PartNumber": 3, "ETag": p1["ETag"]},
                                       {"PartNumber": 1, "ETag": p1["ETag"]}]},
        )
        print("out-of-order parts: accepted (no error)")
    except botocore.exceptions.ClientError as e:
        print(f"out-of-order parts -> {err(e)}")

    # --- 10. abort, then come back with the same id ---
    s3.abort_multipart_upload(Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2)
    for label, call in (
        ("list_parts after abort", lambda: s3.list_parts(Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2)),
        ("upload_part after abort", lambda: s3.upload_part(Bucket=BUCKET, Key="wrong-etag.tar",
                                                          UploadId=uid2, PartNumber=1, Body=parts[3])),
        ("complete after abort", lambda: s3.complete_multipart_upload(
            Bucket=BUCKET, Key="wrong-etag.tar", UploadId=uid2,
            MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": p1["ETag"]}]})),
    ):
        try:
            call()
            print(f"{label}: accepted (no error)")
        except botocore.exceptions.ClientError as e:
            print(f"{label} -> {err(e)}")

    # --- 11. a made-up upload id ---
    try:
        s3.list_parts(Bucket=BUCKET, Key=key, UploadId="not-a-real-upload-id")
        print("bogus upload id: accepted (no error)")
    except botocore.exceptions.ClientError as e:
        print(f"bogus upload id -> {err(e)}")

    # --- 12. what a failed upload leaves behind ---
    left = s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads", [])
    print(f"in-progress uploads left in bucket: {len(left)}")
    s3.delete_object(Bucket=BUCKET, Key=key)
    for u in left:
        s3.abort_multipart_upload(Bucket=BUCKET, Key=u["Key"], UploadId=u["UploadId"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18334")
