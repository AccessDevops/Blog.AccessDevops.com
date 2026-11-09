#!/usr/bin/env python3
"""CRC64/NVME probe: the checksum AWS made the default, and what an
S3-compatible endpoint actually does with it.

    python3 scripts/checksum-probe.py crc
    python3 scripts/checksum-probe.py probe http://127.0.0.1:8333 demo demosecret123

`crc` needs nothing but the standard library; it checks the implementation
against AWS's own published vectors. `probe` needs boto3 and a running
S3-compatible endpoint; it creates a bucket named `crc-probe`.
"""
import base64
import json
import sys

# CRC-64/NVME: width 64, poly 0xAD93D23594C935A9, init all-ones,
# refin/refout true, xorout all-ones. Fed LSB-first, the polynomial constant
# that reproduces the published check values is the reflected one below.
POLY_REFLECTED = 0x9A6C9329AC4BC9B5
INIT = 0xFFFFFFFFFFFFFFFF
XOROUT = 0xFFFFFFFFFFFFFFFF

_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ (POLY_REFLECTED if _c & 1 else 0)
    _TABLE.append(_c)


def crc64nvme(data: bytes) -> int:
    crc = INIT
    for byte in data:
        crc = _TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ XOROUT


def b64(value: int) -> str:
    return base64.b64encode(value.to_bytes(8, "big")).decode()


VECTORS = [
    (b"", 0x0000000000000000),
    (b"123456789", 0xAE8B14860A799888),
    (b"Hello World!", 0x02E51CC85EFCE1A5),
]


def crc_mode():
    rows = []
    for data, expected in VECTORS:
        got = crc64nvme(data)
        rows.append({
            "input": data.decode() or "(empty)",
            "crc64nvme": hex(got),
            "base64": b64(got),
            "matches_published_vector": got == expected,
        })
    print(json.dumps(rows, indent=1))


def probe(endpoint, key, secret):
    import boto3
    from botocore.config import Config

    sent = []

    def hdr(v):
        return base64.b64encode(v).decode() if isinstance(v, bytes) else v

    def capture(request, **kwargs):
        hdrs = {k.lower(): v for k, v in request.headers.items()}
        sent.append({h: hdr(hdrs[h]) for h in hdrs if "checksum" in h})

    client = boto3.client(
        "s3", endpoint_url=endpoint, aws_access_key_id=key,
        aws_secret_access_key=secret, region_name="us-east-1",
        config=Config(retries={"max_attempts": 1}),
    )
    client.meta.events.register("before-send.s3.PutObject", capture)
    client.meta.events.register("before-send.s3.UploadPart", capture)

    bucket = "crc-probe"
    try:
        client.create_bucket(Bucket=bucket)
    except Exception:
        pass

    body = b"the quick brown fox jumps over the lazy dog " * 1000
    good = b64(crc64nvme(body))
    out = {"endpoint": endpoint, "object_bytes": len(body), "crc64nvme": good}

    def attempt(label, **kwargs):
        del sent[:]
        rec = {"case": label}
        try:
            r = client.put_object(Bucket=bucket, Key=label, Body=body, **kwargs)
            rec["status"] = r["ResponseMetadata"]["HTTPStatusCode"]
            hh = {k.lower(): v for k, v in r["ResponseMetadata"]["HTTPHeaders"].items()}
            rec["response_checksum_headers"] = {
                k: v for k, v in hh.items() if "checksum" in k}
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        rec["sent_checksum_headers"] = sent[:1]
        return rec

    out["cases"] = [
        attempt("no-checksum"),
        attempt("crc64nvme-correct", ChecksumAlgorithm="CRC64NVME",
                ChecksumCRC64NVME=good),
        attempt("crc64nvme-wrong", ChecksumAlgorithm="CRC64NVME",
                ChecksumCRC64NVME=b64(0xDEADBEEFDEADBEEF)),
        attempt("crc32-correct", ChecksumAlgorithm="CRC32",
                ChecksumCRC32=base64.b64encode(
                    __import__("zlib").crc32(body).to_bytes(4, "big")).decode()),
        attempt("crc32-wrong", ChecksumAlgorithm="CRC32",
                ChecksumCRC32=base64.b64encode(b"\x00\x00\x00\x01").decode()),
    ]

    reads = {}
    for key_ in ("crc64nvme-correct", "no-checksum"):
        rec = {}
        try:
            h = client.head_object(Bucket=bucket, Key=key_, ChecksumMode="ENABLED")
            rec["head_checksum_headers"] = {
                k: v for k, v in h.items() if k.lower().startswith("checksum")}
        except Exception as e:
            rec["head_error"] = f"{type(e).__name__}: {e}"
        try:
            g = client.get_object(Bucket=bucket, Key=key_, ChecksumMode="ENABLED")
            g["Body"].read()
            rec["get_checksum_headers"] = {
                k: v for k, v in g.items() if k.lower().startswith("checksum")}
        except Exception as e:
            rec["get_error"] = f"{type(e).__name__}: {e}"
        try:
            a = client.get_object_attributes(
                Bucket=bucket, Key=key_, ObjectAttributes=["Checksum"])
            rec["get_object_attributes"] = a.get("Checksum")
        except Exception as e:
            rec["attributes_error"] = f"{type(e).__name__}: {e}"
        reads[key_] = rec
    out["reads"] = reads

    # multipart: full-object vs composite
    mp = {}
    for ctype in ("FULL_OBJECT", "COMPOSITE"):
        label = f"mp-{ctype.lower()}"
        try:
            m = client.create_multipart_upload(
                Bucket=bucket, Key=label, ChecksumAlgorithm="CRC64NVME",
                ChecksumType=ctype)
            parts = []
            for i in range(1, 3):
                chunk = bytes([i]) * (5 * 1024 * 1024)
                up = client.upload_part(
                    Bucket=bucket, Key=label, UploadId=m["UploadId"],
                    PartNumber=i, Body=chunk, ChecksumAlgorithm="CRC64NVME",
                    ChecksumCRC64NVME=b64(crc64nvme(chunk)))
                parts.append({"ETag": up["ETag"], "PartNumber": i})
            c = client.complete_multipart_upload(
                Bucket=bucket, Key=label, UploadId=m["UploadId"],
                MultipartUpload={"Parts": parts})
            mp[ctype] = {"completed": True,
                         "checksum_type": c.get("ChecksumType"),
                         "checksum_crc64nvme": c.get("ChecksumCRC64NVME")}
        except Exception as e:
            mp[ctype] = {"error": f"{type(e).__name__}: {e}"}
    out["multipart"] = mp
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["crc"]:
        crc_mode()
    elif sys.argv[1:2] == ["probe"]:
        probe(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
        sys.exit(2)
