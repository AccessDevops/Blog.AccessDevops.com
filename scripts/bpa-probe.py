#!/usr/bin/env python3
"""
Which of the four Block Public Access switches a given S3 endpoint implements.

Run it against any endpoint you can point boto3 at. The AWS semantics come from
docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html;
this script only measures what the server in front of you does with them.

    pip install boto3
    python3 scripts/bpa-probe.py --endpoint http://127.0.0.1:15000 --label moto-5.2.6
    python3 scripts/bpa-probe.py --endpoint http://127.0.0.1:18337 --label seaweedfs-4.50
"""
import argparse
import datetime
import json
import urllib.error
import urllib.request

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

PUBLIC_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::BUCKET/*",
        }
    ],
}


def unsigned(url, method="GET"):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def code_of(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return "ok"
    except ClientError as e:
        err = e.response["Error"]
        return f"{err.get('Code')}: {err.get('Message')}"


def run(endpoint, label, bucket):
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="probe",
        aws_secret_access_key="probeprobe",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )
    rows = []
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
    s3.put_object(Bucket=bucket, Key="k.txt", Body=b"hello")
    s3.put_object(Bucket=bucket, Key="j.txt", Body=b"hello")

    base = f"{endpoint.rstrip('/')}/{bucket}"

    # 1. does the endpoint know the operation at all?
    rows.append(("PUT ?publicAccessBlock", code_of(
        s3.put_public_access_block,
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )))
    rows.append(("GET ?publicAccessBlock", code_of(s3.get_public_access_block, Bucket=bucket)))

    # 2. with BlockPublicAcls on, a public ACL must be refused at write time
    rows.append(("PutObjectAcl public-read", code_of(
        s3.put_object_acl, Bucket=bucket, Key="k.txt", ACL="public-read")))

    # 3. with BlockPublicPolicy on, a public bucket policy must be refused
    pol = json.dumps(PUBLIC_POLICY).replace("BUCKET", bucket)
    rows.append(("PutBucketPolicy Principal *", code_of(
        s3.put_bucket_policy, Bucket=bucket, Policy=pol)))

    # 4. what an anonymous client gets while the switches are on
    rows.append(("anon GET object", unsigned(f"{base}/k.txt")))
    rows.append(("anon GET listing", unsigned(f"{base}/?list-type=2")))

    # 5. remove the switches, retry: AWS documents that the grant returns with them
    rows.append(("DELETE ?publicAccessBlock", code_of(
        s3.delete_public_access_block, Bucket=bucket)))
    rows.append(("anon GET after delete", unsigned(f"{base}/k.txt")))

    print(f"\n## {label}  ({endpoint})  {datetime.date.today().isoformat()}\n")
    width = max(len(n) for n, _ in rows) + 2
    for name, value in rows:
        print(f"{name:<{width}} {value}")

    # cleanup so a second run reports the same thing
    for fn in (s3.delete_bucket_policy,):
        try:
            fn(Bucket=bucket)
        except ClientError:
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--label", default="endpoint")
    ap.add_argument("--bucket", default="bpa-probe")
    a = ap.parse_args()
    run(a.endpoint, a.label, a.bucket)
