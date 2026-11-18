#!/usr/bin/env python3
"""ETag probe: the same bytes uploaded four ways, and the four ETags that come back.

    pip install boto3
    python3 scripts/etag-probe.py http://127.0.0.1:18333

The point of the probe is that the object identity S3 reports is a function of
the *upload*, not of the bytes. Same 20 MiB payload, four paths:

    1. one PUT                       -> ETag is the MD5 of the file
    2. multipart, 2 parts of 10 MiB  -> ETag is MD5(part MD5s) + "-2"
    3. multipart, 4 parts of 5 MiB   -> ETag is MD5(part MD5s) + "-4"
    4. CopyObject of case 3          -> ETag becomes the MD5 of the file again

Run on 2026-11-18 against SeaweedFS 4.50 (`weed server -s3`), docker image
chrislusf/seaweedfs:latest, with boto3 1.44.5. The probe creates the bucket
`etag-probe` and deletes its own objects afterwards; pass --keep to inspect.
"""
import argparse
import hashlib
import json
import os
import sys

import boto3
from botocore.config import Config

MIB = 1024 * 1024
KEY = "payload/20mib.bin"


def payload(size: int, seed: int = 20261118) -> bytes:
    """Deterministic pseudo-random bytes: same file on every run, incompressible."""
    out = bytearray()
    block = hashlib.sha256(str(seed).encode()).digest()
    while len(out) < size:
        out += block
        block = hashlib.sha256(block).digest()
    return bytes(out[:size])


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def composite_etag(parts: list[bytes]) -> str:
    """MD5 of the concatenated binary part MD5s, dash, part count. No quotes."""
    joined = b"".join(hashlib.md5(p).digest() for p in parts)
    return f'"{hashlib.md5(joined).hexdigest()}-{len(parts)}"'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint", help="S3 endpoint, e.g. http://127.0.0.1:18333")
    ap.add_argument("--bucket", default="etag-probe")
    ap.add_argument("--keep", action="store_true", help="leave the objects in place")
    args = ap.parse_args()

    s3 = boto3.client(
        "s3",
        endpoint_url=args.endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "probe"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "probesecret"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )
    try:
        s3.create_bucket(Bucket=args.bucket)
    except Exception:
        pass

    data = payload(20 * MIB)
    whole = md5_hex(data)
    results = {"file_md5": whole, "file_size": len(data), "cases": []}

    def head(key: str) -> dict:
        h = s3.head_object(Bucket=args.bucket, Key=key)
        return {"etag": h["ETag"], "size": h["ContentLength"],
                "content_md5": h.get("ContentMD5"),
                "checksum": h.get("ChecksumCRC64NVME") or h.get("ChecksumCRC32C")
                            or h.get("ChecksumCRC32")}

    def record(name: str, key: str, part_sizes: list[int]) -> None:
        h = head(key)
        row = {"case": name, "key": key, "parts": len(part_sizes),
               "part_sizes_mib": [round(p / MIB, 2) for p in part_sizes],
               "size": h["size"], "etag": h["etag"],
               "matches_file_md5": h["etag"].strip('"') == whole,
               "checksum_header": h["checksum"]}
        if len(part_sizes) > 1:
            expected = composite_etag([data[o:o + p] for o, p in
                                       zip([sum(part_sizes[:i]) for i in range(len(part_sizes))],
                                           part_sizes)])
            row["composite_expected"] = expected
            row["matches_composite"] = h["etag"] == expected
        results["cases"].append(row)

    # 1. One PUT.
    s3.put_object(Bucket=args.bucket, Key="payload/single.bin", Body=data)
    record("single PUT, 20 MiB", "payload/single.bin", [20 * MIB])

    # 2. Two parts of 10 MiB.
    for name, parts_mib in (("multipart, 2 x 10 MiB", 10), ("multipart, 4 x 5 MiB", 5)):
        key = f"payload/{parts_mib}mib-parts.bin"
        uid = s3.create_multipart_upload(Bucket=args.bucket, Key=key)["UploadId"]
        sent, offset = [], 0
        for number, size in enumerate([parts_mib * MIB] * (20 // parts_mib), start=1):
            body = data[offset:offset + size]
            r = s3.upload_part(Bucket=args.bucket, Key=key, UploadId=uid,
                               PartNumber=number, Body=body)
            sent.append({"PartNumber": number, "ETag": r["ETag"]})
            offset += size
        s3.complete_multipart_upload(Bucket=args.bucket, Key=key, UploadId=uid,
                                     MultipartUpload={"Parts": sent})
        record(name, key, [parts_mib * MIB] * (20 // parts_mib))

    # 3. CopyObject on the 4-part object: same bytes, single-part write.
    s3.copy_object(Bucket=args.bucket, Key="payload/copied.bin",
                   CopySource={"Bucket": args.bucket, "Key": "payload/5mib-parts.bin"})
    record("CopyObject of the 4-part object", "payload/copied.bin", [20 * MIB])

    # 4. What the listing reports, and whether the quotes survive.
    listing = s3.list_objects_v2(Bucket=args.bucket, Prefix="payload/")
    results["listing"] = {o["Key"]: o["ETag"] for o in listing.get("Contents", [])}

    print(json.dumps(results, indent=2))

    if not args.keep:
        for k in results["listing"]:
            s3.delete_object(Bucket=args.bucket, Key=k)

    # Exit non-zero if a documented behaviour did not reproduce on this endpoint:
    # a reader running the probe against another provider needs to know.
    c = results["cases"]
    ok = (c[0]["matches_file_md5"] and c[1]["matches_composite"]
          and c[2]["matches_composite"] and not c[1]["matches_file_md5"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
