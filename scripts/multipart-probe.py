#!/usr/bin/env python3
"""Multipart upload probe: the 5 MiB floor, the 10,000-part ceiling, and the
part size the AWS SDK chooses when the arithmetic stops fitting.

    python3 scripts/multipart-probe.py plan
    python3 scripts/multipart-probe.py probe http://127.0.0.1:18333

`plan` needs only `boto3` installed. `probe` needs a running S3-compatible
endpoint; it creates a bucket called `mp-probe` and uploads a few megabytes.

Ran on 2026-11-06 against SeaweedFS 4.50 (`weed server -s3`, docker image
chrislusf/seaweedfs:latest). Both limits are enforced, and at different
moments: the floor at CompleteMultipartUpload, the ceiling at UploadPart.

    pip install boto3
"""
import sys, json, math

MIB = 1024 * 1024
GIB = 1024 * MIB
TIB = 1024 * GIB
MAX_PARTS = 10_000
MIN_PART = 5 * MIB
MAX_PART = 5 * GIB

SIZES = [
    ("60 GiB", 60 * GIB),
    ("500 GiB", 500 * GIB),
    ("1 TiB", 1 * TIB),
    ("5 TiB", 5 * TIB),
    ("48.8 TiB", int(48.8 * TIB)),
]


def plan():
    """Two columns: what the limits force, and what the SDK actually picks."""
    from s3transfer.utils import ChunksizeAdjuster

    adjuster = ChunksizeAdjuster()
    default_chunk = 8 * MIB  # s3transfer.manager.TransferConfig default
    rows = []
    for label, size in SIZES:
        required = max(MIN_PART, math.ceil(size / MAX_PARTS))
        chosen = adjuster.adjust_chunksize(default_chunk, size)
        rows.append(
            {
                "object": label,
                "bytes": size,
                "min_part_to_fit_10000": required,
                "sdk_chunk_size": chosen,
                "sdk_parts": math.ceil(size / chosen),
                "last_part": size - chosen * (math.ceil(size / chosen) - 1),
            }
        )
    print(json.dumps({"max_object_if_5gib_parts": MAX_PARTS * MAX_PART,
                      "rows": rows}, indent=1))


def probe(endpoint):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    bucket = "mp-probe"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="probe",
        aws_secret_access_key="probesecret",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 1}),
    )
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError:
        pass

    def mpu(parts, key):
        uid = s3.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]
        listed = []
        for i, size in enumerate(parts, start=1):
            r = s3.upload_part(Bucket=bucket, Key=key, UploadId=uid,
                               PartNumber=i, Body=b"x" * size)
            listed.append({"ETag": r["ETag"], "PartNumber": i})
        try:
            s3.complete_multipart_upload(Bucket=bucket, Key=key, UploadId=uid,
                                         MultipartUpload={"Parts": listed})
            head = s3.head_object(Bucket=bucket, Key=key)
            return {"complete": "ok", "stored_bytes": head["ContentLength"],
                    "etag": head["ETag"]}
        except ClientError as e:
            err = e.response["Error"]
            return {"complete": "rejected",
                    "http": e.response["ResponseMetadata"]["HTTPStatusCode"],
                    "code": err.get("Code"), "message": err.get("Message")}

    cases = [
        ("four non-final parts at 1 MiB", [MIB, MIB, MIB, 1024], "small-1mib"),
        ("one non-final part at 5 MiB minus 1 byte", [5 * MIB - 1, MIB], "off-by-one"),
        ("two non-final parts at 5 MiB, 1 KiB tail", [5 * MIB, 5 * MIB, 1024], "big-5mib"),
        ("single part, 1 KiB", [1024], "single-part"),
    ]
    for label, parts, key in cases:
        out = {"case": label, "part_sizes": parts}
        out.update(mpu(parts, key))
        print(json.dumps(out))

    uid = s3.create_multipart_upload(Bucket=bucket, Key="ceiling")["UploadId"]
    for n in (9_999, 10_000, 10_001):
        try:
            s3.upload_part(Bucket=bucket, Key="ceiling", UploadId=uid,
                           PartNumber=n, Body=b"x")
            print(json.dumps({"part_number": n, "accepted": True}))
        except ClientError as e:
            err = e.response["Error"]
            print(json.dumps({"part_number": n, "accepted": False,
                              "http": e.response["ResponseMetadata"]["HTTPStatusCode"],
                              "code": err.get("Code"), "message": err.get("Message")}))
    s3.abort_multipart_upload(Bucket=bucket, Key="ceiling", UploadId=uid)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        plan()
    elif len(sys.argv) >= 3 and sys.argv[1] == "probe":
        probe(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
