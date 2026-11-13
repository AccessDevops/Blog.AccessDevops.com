#!/usr/bin/env python3
"""Does re-sending a part number replace the part, or does it race?

    python3 scripts/resume-overwrite-probe.py http://127.0.0.1:18334 10 0
    python3 scripts/resume-overwrite-probe.py http://127.0.0.1:18334 10 0.5

Each trial: initiate an upload, send part 1 (block A), send part 1 again with
different bytes (block B), read ListParts, complete with the ETag ListParts
returned, then hash the stored object to see which block landed. The last two
arguments are the trial count and the sleep between the second upload and
ListParts.

Ran 2026-11-13 against SeaweedFS 4.50 and moto 5.2.5.
"""
import hashlib
import sys
import time

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


def block(tag, size):
    return (hashlib.sha256(tag.encode()).digest() * (size // 32 + 2))[:size]


def main(endpoint, trials, pause):
    s3 = client(endpoint)
    try:
        s3.create_bucket(Bucket=BUCKET)
    except botocore.exceptions.ClientError:
        pass
    a, b = block("block-A", 5 * MIB), block("block-B", 5 * MIB)
    ha, hb = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()

    stale = landed_old = 0
    for i in range(trials):
        key = f"overwrite-{i}.bin"
        uid = s3.create_multipart_upload(Bucket=BUCKET, Key=key)["UploadId"]
        s3.upload_part(Bucket=BUCKET, Key=key, UploadId=uid, PartNumber=1, Body=a)
        second = s3.upload_part(Bucket=BUCKET, Key=key, UploadId=uid, PartNumber=1, Body=b)
        if pause:
            time.sleep(pause)
        listed = s3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid)["Parts"][0]["ETag"]
        is_stale = listed != second["ETag"]
        stale += is_stale
        s3.complete_multipart_upload(
            Bucket=BUCKET, Key=key, UploadId=uid,
            MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": listed}]},
        )
        got = hashlib.sha256(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()).hexdigest()
        which = "B" if got == hb else "A" if got == ha else "?"
        landed_old += which == "A"
        print(
            f"trial {i + 1}: upload_part ETag {second['ETag']} · "
            f"list_parts ETag {listed} · stale={is_stale} · stored block {which}"
        )
        s3.delete_object(Bucket=BUCKET, Key=key)

    print(f"\n{trials} trials, pause {pause}s: {stale} stale ListParts replies, "
          f"{landed_old} objects holding the first block")


if __name__ == "__main__":
    main(
        sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18334",
        int(sys.argv[2]) if len(sys.argv) > 2 else 10,
        float(sys.argv[3]) if len(sys.argv) > 3 else 0.0,
    )
