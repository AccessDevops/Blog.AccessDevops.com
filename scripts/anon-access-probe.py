#!/usr/bin/env python3
"""Measure which anonymous S3 requests a bucket actually answers, one grant at a time.

Reproduces the table in content/blog/anonymous-read-exact-leak-path.md.

    python3 scripts/anon-access-probe.py --endpoint http://127.0.0.1:18335 \
        --access-key probe --secret-key probesecret

Requires boto3. The endpoint must be an S3 server that enforces authentication:
a server started without an identities file answers 200 to everything and the
matrix below is meaningless.
"""
import argparse
import json
import urllib.error
import urllib.request

import boto3
from botocore.config import Config


def anon(endpoint, path, method="GET"):
    """Send an unsigned request. Returns (status, code) where code is the S3 <Code>."""
    req = urllib.request.Request(endpoint + path, method=method, data=b"" if method == "PUT" else None)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(4096).decode("utf-8", "replace")
            code = "200" if r.status == 200 else r.status
    except urllib.error.HTTPError as e:
        body = e.read(4096).decode("utf-8", "replace")
        code = e.code
    start = body.find("<Code>")
    if start >= 0:
        code = f"{code} {body[start + 6:body.find('</Code>', start)]}"
    return str(code)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", required=True)
    p.add_argument("--bucket", default="anon-probe")
    p.add_argument("--access-key", default="probe")
    p.add_argument("--secret-key", default="probesecret")
    a = p.parse_args()

    s3 = boto3.client(
        "s3",
        endpoint_url=a.endpoint,
        aws_access_key_id=a.access_key,
        aws_secret_access_key=a.secret_key,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 0}),
    )
    b, k = a.bucket, "k.txt"
    s3.create_bucket(Bucket=b)
    s3.put_object(Bucket=b, Key=k, Body=b"private\n")

    def row(label):
        print(f"{label:<34} GET {anon(a.endpoint, f'/{b}/{k}'):<22} "
              f"LIST {anon(a.endpoint, f'/{b}?list-type=2'):<22} "
              f"PUT {anon(a.endpoint, f'/{b}/x.txt', 'PUT')}")

    row("no grant")
    s3.put_object_acl(Bucket=b, Key=k, ACL="public-read")
    row("object ACL public-read")
    s3.put_object_acl(Bucket=b, Key=k, ACL="private")
    s3.put_bucket_acl(Bucket=b, ACL="public-read")
    row("bucket ACL public-read")
    s3.put_bucket_acl(Bucket=b, ACL="private")

    get_only = {
        "Version": "2012-10-17",
        "Statement": [{"Sid": "PublicRead", "Effect": "Allow", "Principal": "*",
                       "Action": ["s3:GetObject"],
                       "Resource": [f"arn:aws:s3:::{b}/*"]}],
    }
    s3.put_bucket_policy(Bucket=b, Policy=json.dumps(get_only))
    row("policy: Principal * GetObject")
    s3.delete_bucket_policy(Bucket=b)
    row("policy deleted, ACLs private")


if __name__ == "__main__":
    main()
