---
title: "Parallel parts beat one stream, until the client is the limit"
description: "Ten settings, one 256 MiB file, one endpoint: parts in flight raise throughput until the client's own CPU takes over. The whole grid, measured."
date: 2026-11-16
author: "Clement Baranger"
tags: ["s3", "performance", "uploads"]
guide: incomplete-multipart-uploads
related: [multipart-5mb-floor-10000-parts, resume-interrupted-multipart-upload]
---

Sixteen parts in flight is the standard advice, and it is neither wrong nor free. On one machine, the same 256 MiB file uploaded 2.5 times faster with four parts in flight than with one, stopped improving after that, and came in a quarter slower at sixteen with 8 MiB parts — using more CPU seconds to move fewer bytes. The setting everyone copies is not a throughput setting but a position on a curve, and the curve bends where your own machine gives out.

## The short version

- Splitting a file into parts only helps when several parts travel at the same time. One part at a time is slower than one plain request: 26.6 MiB/s against 59.2.
- Throughput gains about 2.5× between one part in flight and four, at both part sizes measured, then stops improving and falls back at sixteen.
- The ceiling was the client, not the server: 1.4 of 6 vCPU busy reading, checksumming and sending each part.
- Defaults disagree wildly — 10 requests in boto3 and the AWS CLI, 4 per file in rclone, 256 file workers in s5cmd — so "the default" describes a tool, not a practice.
- At the rates measured here, the same 500 GiB backup is a 5.3-hour job at 26.6 MiB/s and a 1.3-hour job at 107.

## What actually happens

A multipart upload is three calls and a loop. `CreateMultipartUpload` opens the upload and returns an ID; each `UploadPart` carries a part number and some bytes; `CompleteMultipartUpload` sends the ascending list of numbers with their ETags. The loop is where a client decides how many `UploadPart` requests to keep open — `max_concurrency` in boto3, `max_concurrent_requests` in the AWS CLI, `--s3-upload-concurrency` in rclone, `--concurrency` in s5cmd.

Every part is a complete HTTP request, not a slice of a stream: headers, a signature, a body, a client-side checksum, its own response, its own round trip. Which of those costs you depends on where the endpoint is. **On a slow link, requests spend their life waiting** — round trip, first byte, window — so ten in parallel return ten times the bytes until the link is full; that is the regime every "increase concurrency" article describes, and it is real. **On a fast link, the client is the bottleneck**: nothing waits, so what remains is preparing and sending bodies — read, digest, sign, write, read the response — and ten threads competing for the same cores add context switches rather than bytes. I measured that second regime, because no vendor page describes it: one 256 MiB file, uploaded ten ways to SeaweedFS 4.50 on the same 6 vCPU host, through `boto3` 1.34.46 over loopback, five runs each, medians with the min-max spread:

| Parts in flight | 8 MiB parts | 32 MiB parts | Client CPU (8 MiB run) |
|---|---|---|---|
| 1 | 26.6 MiB/s (23.4–34.3) | 43.4 MiB/s (38.1–50.9) | 0.41 cores |
| 2 | 54.3 MiB/s (44.2–59.1) | 65.7 MiB/s (52.8–73.8) | 0.77 cores |
| 4 | 65.2 MiB/s (49.8–90.2) | 107.0 MiB/s (57.8–116.7) | 1.21 cores |
| 8 | 79.1 MiB/s (69.0–89.9) | 99.6 MiB/s (62.4–103.8) | 1.33 cores |
| 16 | 59.3 MiB/s (48.6–99.1) | 94.5 MiB/s (82.1–109.9) | 1.39 cores |
| one plain `PUT`, no parts | 59.2 MiB/s (47.9–88.9) | — | 0.63 cores |

```bash
python3 scripts/concurrency-probe.py run http://127.0.0.1:18333 bench --size-mib 256 --reps 5
```

![Bar chart of upload throughput in MiB/s against parts in flight for 8 MiB and 32 MiB parts, with min-max whiskers and a dashed single-PUT baseline at 59.2 MiB/s: one thread with parts is slower than a single request, the peak is four parts in flight, and past that throughput falls while client CPU use climbs](/diagrams/parallel-parts-vs-single-stream.svg)

Three things there matter more than the peak. **One thread with parts is a downgrade**: 26.6 MiB/s against 59.2 for a plain `PUT`, and the best of the five 8 MiB runs (34.3) stayed below the worst single-PUT run (47.9), so it is not noise. **Part count costs requests**: 256 MiB is 32 parts at 8 MiB and 8 at 32 MiB, and the configuration with a quarter of the requests was 1.6× faster at equal concurrency. **The shape is the point**: CPU per second rose from 0.41 to 1.39 cores while throughput fell back, which is what a saturated client looks like.

The grid is bounded by [the 5 MiB part floor and the 10,000-part ceiling](/blog/multipart-5mb-floor-10000-parts), which decide which part sizes are legal and are checked at different moments of the upload.

## Where it bites

**One run is not a measurement.** The same configuration here ranged from 47.9 to 88.9 MiB/s across five runs — a wider spread than most of the differences in the table. Sizing on one `time` invocation is how a team ends up with a concurrency of 32 that felt fast for a week.

**"Multipart is faster" is not a rule, and rclone says so.** Its documentation warns that single-part transfers can be faster or slower than multipart "depending on your latency from S3 — the more latency, the more likely single part transfers will be faster". The table above shows the same shape with no latency at all, which is the useful part: multipart optimises for waiting, so it costs you when there is nothing to wait for.

**The defaults are not comparable.** Each tool counts something different:

| Tool | Setting | Default |
|---|---|---|
| boto3 / `s3transfer` | `max_concurrency` | 10 |
| AWS CLI `s3 cp`/`sync` | `max_concurrent_requests` | 10 |
| rclone | `--s3-upload-concurrency` | 4 per file |
| s5cmd | `--numworkers` / `--concurrency` | 256 files / 5 parts per file |

**Concurrency is memory.** rclone documents the cost as `--transfers × --s3-upload-concurrency × --s3-chunk-size`. Sixteen parts of 32 MiB is 512 MiB of buffer for one file; multiply by the files in flight and a 2 GB container dies before its first completion.

**Raising it can make the server say no.** AWS documents at least 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD requests per second per partitioned prefix, and answers above that with code `SlowDown`, "Reduce your request rate." A client that retries harder feeds the condition; one that lowers concurrency recovers. The unit is requests, not bytes, so when request rate is the ceiling the lever is a larger part size.

**A crashed upload keeps its parts, and they keep being billed** — the numbers are in [what survives when the process dies mid-upload](/blog/resume-interrupted-multipart-upload).

## Doing it right

**1. Measure the grid before choosing a number.** Four to eight configurations, three to five runs each, median rather than best. The probe takes the file size, the endpoint and the matrix:

```bash
docker run -d --name weed-bench -p 127.0.0.1:18333:8333 \
  chrislusf/seaweedfs:latest server -dir=/data -s3 -s3.port=8333
python3 scripts/concurrency-probe.py run http://127.0.0.1:18333 bench --size-mib 256 --reps 5
```

**2. Pick the knee, not the peak.** Take the smallest concurrency within about 5% of the best median, at the largest part size the memory allows. Above, that is 4 parts of 32 MiB: 107 MiB/s for 128 MiB of buffer, where 16 parts of 8 MiB got 59 MiB/s for the same buffer and more CPU.

**3. Set it explicitly, in code, next to the reason — and bound the buffer in the same commit.**

```python
from boto3.s3.transfer import TransferConfig

MIB = 1024**2
# Measured 2026-11-16 against this endpoint: knee at 4 parts of 32 MiB,
# 107 MiB/s; 16 parts of 8 MiB was slower and used more CPU.
# Buffer cost: 4 x 32 MiB = 128 MiB per transfer.
cfg = TransferConfig(
    multipart_threshold=8 * MIB,
    multipart_chunksize=32 * MIB,
    max_concurrency=4,
)
s3.upload_file(path, "backups-prod", key, Config=cfg)
```

**4. Treat `SlowDown` as backpressure.** Cap concurrency, add jittered backoff, log requests per second; if the ceiling is request rate, raise the part size rather than the thread count.

**5. Re-measure per endpoint.** The same client against R2, B2, MinIO or a self-hosted gateway has a different knee: a value tuned on loopback is an upper bound, not a setting.

## How S3 Explorer fits

A concurrency number only means something against a named endpoint, so the useful workflow compares two of them from one window. S3 Explorer's **provider picker** carries 25 presets across Cloud, Specialist, Self-hosted and Enterprise plus a Custom tile for endpoint, region and addressing style; **test connection** reports how many buckets those credentials can see before a profile is saved; the **per-request metrics** panel counts the `LIST`, `GET` and other calls a session generated, where a runaway retry loop becomes visible. Several profiles stay open at once. [S3 Explorer](https://s3explorer.accessdevops.com/guides/incomplete-multipart-uploads/?utm_source=blog&utm_medium=in_article&utm_campaign=parallel-parts-vs-single-stream) runs on Windows, macOS and Linux.

## Checklist

- [ ] The concurrency in use was measured on this endpoint and client, with at least three runs.
- [ ] Part size and count were chosen together, and the object fits in 10,000 parts with room to spare.
- [ ] `max_concurrency × multipart_chunksize` is written down and fits the per-transfer memory budget.
- [ ] No path uses multipart with one part in flight where a single `PUT` would do.
- [ ] `SlowDown` triggers a backoff that lowers concurrency, logged with requests per second.
- [ ] The setting lives in code with its measurement date beside it.
- [ ] The grid has been re-run against every endpoint in production, not only the first one.

## Sources

- [Amazon S3 — best practices design patterns for performance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html): "at least 3,500 PUT/COPY/POST/DELETE or 5,500 GET/HEAD requests per second per partitioned Amazon S3 prefix"; scaling is gradual and returns `503 Slow Down` while it happens.
- [Amazon S3 — error code catalogue](https://docs.aws.amazon.com/AmazonS3/latest/API/API_Error.html): `SlowDown` — "Reduce your request rate", HTTP 503 Slow Down.
- [boto3 — S3 transfer configuration](https://docs.aws.amazon.com/boto3/latest/reference/customizations/s3.html): `TransferConfig.DEFAULTS` — `max_concurrency: 10`, `multipart_chunksize: 8388608`, `multipart_threshold: 8388608`.
- [AWS CLI — S3 configuration](https://docs.aws.amazon.com/cli/latest/topic/s3-config.html): `max_concurrent_requests` default 10, `multipart_chunksize` default 8 MB.
- [rclone — Amazon S3 backend](https://rclone.org/s3/): the memory formula `--transfers × --s3-upload-concurrency × --s3-chunk-size`, the note that "single part transfers can be faster than multipart transfers or slower depending on your latency from S3", and default 4 in [the source](https://github.com/rclone/rclone/blob/master/backend/s3/s3.go).
- [s5cmd](https://github.com/peak/s5cmd): `numworkers` default 256, per-file `--concurrency` default 5.
- Measured 16 November 2026 on a 6 vCPU KVM host: boto3 1.34.46, SeaweedFS 4.50 (`weed server -s3`) in Docker on the same machine, loopback, 256 MiB file, five runs per configuration, medians with min-max. Probe: `scripts/concurrency-probe.py`; chart: `scripts/concurrency-diagram.py`. The absolute figures describe that host; the shape is the transferable part.
