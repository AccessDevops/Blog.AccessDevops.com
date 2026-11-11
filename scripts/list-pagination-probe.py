#!/usr/bin/env python3
"""Measure ListObjectsV2 pagination on any S3 endpoint.

Fills a bucket with a known key layout, then pages through it and prints what
the endpoint actually returned: page sizes, KeyCount, IsTruncated, whether
CommonPrefixes share the MaxKeys budget, and whether MaxKeys above 1,000 is
honoured.

    python3 scripts/list-pagination-probe.py fill http://127.0.0.1:8333 listprobe
    python3 scripts/list-pagination-probe.py run  http://127.0.0.1:8333 listprobe

Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, defaulting to
the SeaweedFS demo identity used in the article.
"""
import json
import os
import sys

import boto3
from botocore.config import Config

AK = os.environ.get("AWS_ACCESS_KEY_ID", "demo")
SK = os.environ.get("AWS_SECRET_ACCESS_KEY", "demosecret123")


def client(endpoint):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=AK,
        aws_secret_access_key=SK,
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
    )


def ensure_bucket(s3, bucket):
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception:
        pass


def fill(endpoint, bucket):
    s3 = client(endpoint)
    ensure_bucket(s3, bucket)
    blobs = [
        ("small", b"x"),
        # 2,501 flat keys, so the pages are 1000 / 1000 / 501.
        *[(f"flat/{i:04d}", b"x") for i in range(2501)],
        # Numeric-looking names: lexicographic order puts 10 before 9.
        *[(f"order/{i}", b"x") for i in (1, 2, 9, 10, 100)],
        # 990 root objects then 50 distinct sub-prefixes under mixed/.
        *[(f"mixed/a{i:04d}.txt", b"x") for i in range(990)],
        *[(f"mixed/b{i:04d}/file.dat", b"x") for i in range(50)],
    ]
    for key, body in blobs:
        s3.put_object(Bucket=bucket, Key=key, Body=body)
    print(json.dumps({"filled": len(blobs), "bucket": bucket}))


def page(s3, bucket, **kw):
    r = s3.list_objects_v2(Bucket=bucket, **kw)
    contents = [o["Key"] for o in r.get("Contents", [])]
    prefixes = [p["Prefix"] for p in r.get("CommonPrefixes", [])]
    return {
        "max_keys_sent": kw.get("MaxKeys", "default"),
        "contents": len(contents),
        "common_prefixes": len(prefixes),
        "key_count": r.get("KeyCount"),
        "is_truncated": r.get("IsTruncated"),
        "token": "yes" if r.get("NextContinuationToken") else "no",
        "first": contents[0] if contents else (prefixes[0] if prefixes else None),
        "last": contents[-1] if contents else (prefixes[-1] if prefixes else None),
    }


def run(endpoint, bucket):
    s3 = client(endpoint)
    out = {}

    # A. Default page size over 2,501 flat keys.
    pages, token = [], None
    while True:
        r = s3.list_objects_v2(Bucket=bucket, Prefix="flat/", **({"ContinuationToken": token} if token else {}))
        pages.append({
            "contents": len(r.get("Contents", [])),
            "key_count": r.get("KeyCount"),
            "is_truncated": r.get("IsTruncated"),
            "token_chars": len(r.get("NextContinuationToken", "")),
        })
        token = r.get("NextContinuationToken")
        if not r.get("IsTruncated"):
            break
    out["flat_default_pages"] = pages

    # B. Ask for 5,000 keys in one page: is MaxKeys a request or a cap?
    out["max_keys_5000"] = page(s3, bucket, Prefix="flat/", MaxKeys=5000)
    out["max_keys_0"] = page(s3, bucket, Prefix="flat/", MaxKeys=0)

    # C. Delimiter: 990 objects + 50 rolled-up prefixes under mixed/.
    out["delimiter_max_1000"] = page(s3, bucket, Prefix="mixed/", Delimiter="/", MaxKeys=1000)
    out["delimiter_max_10"] = page(s3, bucket, Prefix="mixed/", Delimiter="/", MaxKeys=10)
    out["mixed_flat_total"] = page(s3, bucket, Prefix="mixed/", MaxKeys=1000)

    # D. The loop that compares len(Contents) with MaxKeys.
    r = s3.list_objects_v2(Bucket=bucket, Prefix="mixed/", Delimiter="/", MaxKeys=1000)
    naive_stops = len(r.get("Contents", [])) < 1000 and not r.get("IsTruncated")
    out["naive_loop_stops_early"] = bool(naive_stops) or (
        len(r.get("Contents", [])) < 1000 and r.get("IsTruncated")
    )
    out["naive_loop_detail"] = {
        "contents": len(r.get("Contents", [])),
        "is_truncated": r.get("IsTruncated"),
    }

    # E. Ordering: UTF-8 binary, not numeric.
    out["ordering"] = [o["Key"] for o in
                       s3.list_objects_v2(Bucket=bucket, Prefix="order/").get("Contents", [])]

    # F. StartAfter versus ContinuationToken.
    out["start_after"] = page(s3, bucket, Prefix="flat/", StartAfter="flat/1000", MaxKeys=5)

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("fill", "run"):
        print(__doc__)
        sys.exit(2)
    {"fill": fill, "run": run}[sys.argv[1]](sys.argv[2], sys.argv[3])
