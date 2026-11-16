#!/usr/bin/env python3
"""Concurrency probe: what actually changes multipart upload throughput.

    python3 scripts/concurrency-probe.py run http://127.0.0.1:18333 bench-bucket
    python3 scripts/concurrency-probe.py run http://127.0.0.1:18333 bench-bucket --size-mib 256

Uploads the same file repeatedly with different part sizes and different
numbers of parts in flight, and reports elapsed time, throughput and the CPU
seconds the client spent doing it. boto3 only; no other dependency.

Why CPU seconds matter: on a fast local endpoint the plateau is not the
network and not the server, it is the client process hashing every part
(MD5 for the ETag) on one GIL-bound thread.
"""
import argparse
import hashlib
import os
import resource
import statistics
import sys
import time

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

MIB = 1024**2


def make_file(path, size):
    """Deterministic content, so two runs hash the same bytes."""
    if os.path.exists(path) and os.path.getsize(path) == size:
        return path
    block = b"".join(hashlib.sha256(str(i).encode()).digest() for i in range(1024))  # 32 KiB
    with open(path, "wb") as fh:
        written = 0
        while written < size:
            chunk = block[: min(len(block), size - written)]
            fh.write(chunk)
            written += len(chunk)
    return path


def cpu_seconds():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def one_run(client, bucket, path, key, part_mib, concurrency, single_put):
    size = os.path.getsize(path)
    c0, t0 = cpu_seconds(), time.perf_counter()
    if single_put:
        with open(path, "rb") as fh:
            client.put_object(Bucket=bucket, Key=key, Body=fh)
    else:
        cfg = TransferConfig(
            multipart_threshold=8 * MIB,
            multipart_chunksize=part_mib * MIB,
            max_concurrency=concurrency,
            use_threads=True,
        )
        client.upload_file(path, bucket, key, Config=cfg)
    elapsed = time.perf_counter() - t0
    cpu = cpu_seconds() - c0
    return {
        "part_mib": part_mib,
        "concurrency": concurrency,
        "single_put": single_put,
        "seconds": round(elapsed, 3),
        "mib_s": round(size / MIB / elapsed, 1),
        "cpu_s": round(cpu, 2),
        "cpu_per_s": round(cpu / elapsed, 2),
    }


def run(args):
    s3 = boto3.client(
        "s3",
        endpoint_url=args.endpoint,
        aws_access_key_id="probe",
        aws_secret_access_key="probesecret123",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 1}),
    )
    bucket = args.bucket
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception as e:  # noqa: BLE001 - already exists is fine
        print(f"# bucket: {type(e).__name__} {e}", file=sys.stderr)

    size = args.size_mib * MIB
    path = make_file(f"/tmp/concurrency-probe-{args.size_mib}.bin", size)
    print(f"# file {path} {size} bytes, {args.reps} reps per configuration")
    print(f"# client: {os.cpu_count()} vCPU, boto3 {boto3.__version__}, endpoint {args.endpoint}")

    matrix = [("single PUT", 8, 0, True)]
    for part in (8, 32):
        for conc in (1, 2, 4, 8, 16):
            matrix.append((f"{part} MiB parts", part, conc, False))

    rows = []
    for label, part, conc, single in matrix:
        samples = []
        for rep in range(args.reps):
            key = f"probe/{label.replace(' ', '-')}/{rep}.bin"
            samples.append(one_run(s3, bucket, path, key, part, conc, single))
            s3.delete_object(Bucket=bucket, Key=key) if False else None
        med = {k: statistics.median([s[k] for s in samples]) for k in
               ("seconds", "mib_s", "cpu_s", "cpu_per_s")}
        lo = min(s["mib_s"] for s in samples)
        hi = max(s["mib_s"] for s in samples)
        row = {"label": label, "part_mib": part, "concurrency": conc, **med,
               "mib_s_min": lo, "mib_s_max": hi}
        rows.append(row)
        print(f"{label:<14} conc={conc:<3} {med['mib_s']:>7.1f} MiB/s "
              f"[{lo:.1f}-{hi:.1f}]  {med['seconds']:>6.2f}s  cpu {med['cpu_s']:>5.2f}s "
              f"({med['cpu_per_s']:.2f} cores)", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("endpoint")
    p.add_argument("bucket", nargs="?", default="concurrency-probe")
    p.add_argument("--size-mib", type=int, default=256)
    p.add_argument("--reps", type=int, default=3)
    p.set_defaults(func=run)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
