---
title: "S3's 128 KB rule: what it does to transitions and bills"
description: "One threshold, three behaviours: lifecycle skips objects under 128 KB, Standard-IA bills them as 128 KB, Intelligent-Tiering ignores them."
date: 2026-11-27
author: "Clement Baranger"
tags: ["s3", "lifecycle", "cost"]
guide: s3-storage-pricing-comparison
related: [incomplete-multipart-storage-leak, s3-total-cost-of-ownership]
---

A service writes a million small files into one S3 prefix — log fragments, thumbnails, 8 KB each — and a lifecycle rule says "after 30 days, move the prefix to Standard-IA". The console shows the rule enabled. On a bucket created last year that rule moves nothing at all; on one where somebody forced it, the monthly bill for those 7.45 GiB goes from $0.17 to $11.53. Both outcomes come from the same number.

## The short version

- S3 has one size threshold, 128 KB, and applies it three ways: transitions skip objects smaller than that, Standard-IA bills them as if they were, Intelligent-Tiering neither tiers nor charges them.
- From the published price list: 1,000,000 objects of 8,000 bytes cost $0.17 a month in S3 Standard, $1.53 in Standard-IA, and $11.53 in the month they move, because a transition is charged per object.
- Below 71,235 bytes an object is dearer in Standard-IA than in Standard before any request is counted. Most prefixes people call "cold" sit under that line.
- "The rule ran and nothing moved" is the documented default since September 2024, not a fault — and a configuration written before then keeps the older behaviour until somebody edits it.
- The minimum charge follows the object, not the rule: a PUT that writes straight into Standard-IA never passes a lifecycle filter and pays for 128 KB whatever it uploaded.

## What actually happens

A lifecycle transition is a copy: S3 reads each object, writes it into another storage class, and charges one request per object — $0.01 per 1,000 transitions into Standard-IA in the us-east-1 price list. A million fragments therefore cost $10.00 to move, 58 times the monthly storage bill of the whole prefix. The fee is fixed per object; the saving is proportional to size.

The second half is the minimum billable size, and AWS answers it with a worked example in the [S3 FAQ](https://aws.amazon.com/s3/faqs/): a 6 KB object in Standard-IA is charged for 6 KB plus a minimum object size charge equivalent to 122 KB, because "S3 Standard-IA is designed for larger objects and has a minimum object storage charge of 128KB". The [storage class table](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html) repeats the figure in a column, next to a 30-day minimum duration. One Zone-IA and Glacier Instant Retrieval carry the same 128 KB minimum, at $0.01 and $0.004 per GB-month.

![Bar chart of one million 8,000-byte objects priced for one month: S3 Standard and Intelligent-Tiering at $0.17, Standard-IA at $1.53 of storage plus $10.00 of transition requests for $11.53, One Zone-IA at $1.22 plus $10.00 for $11.22, with a footnote giving Glacier Instant Retrieval at $0.49 of storage and $20.00 of requests](/diagrams/intelligent-tiering-128kb-rule.svg)

I priced the workload from the offer file rather than from memory. The script downloads the us-east-1 price list, reads the storage, transition and monitoring prices out of it, and applies the minimum where the class has one. This run used the file published on 25 November 2026, offer version `20261125152611`:

```bash
python3 scripts/tiering-cost-model.py --objects 1000000 --size 8KB
```

| storage class | $/GB-month | storage | transition requests | first month |
| --- | --- | --- | --- | --- |
| S3 Standard | 0.02300 | $0.17 | — | $0.17 |
| Standard-IA | 0.01250 | $1.53 | $10.00 | $11.53 |
| One Zone-IA | 0.01000 | $1.22 | $10.00 | $11.22 |
| Glacier Instant Retrieval | 0.00400 | $0.49 | $20.00 | $20.49 |
| Intelligent-Tiering | 0.02300 | $0.17 | $0.00 | $0.17 |

The third row is the one to read. Storage alone is 8.9 times the Standard bill, because a million objects billed at 128 KB each is 122.07 GiB for 7.45 GiB of data — 16 times the bytes that exist. Of that $1.53, $1.43 is the minimum-size charge. The price list carries it as its own usage type, `TimedStorage-SIA-SmObjects`.

Intelligent-Tiering is the row people misread in both directions. Objects below 128 KB are never monitored and never tiered; the [FAQ](https://aws.amazon.com/s3/faqs/) says they "will always be charged at the Frequent Access tier rates, with no monitoring and automation charge". Adopting it for a small-object bucket therefore costs nothing and saves nothing — the objects stay in the Frequent Access tier at $0.023. Above 128 KB the monitoring fee of $0.0025 per 1,000 objects a month applies, $2.50 per million, and the script shows it equals the Standard-to-IA saving at about 250 KiB per object.

## Where it bites

**The transition that silently skips.** The [transition constraints](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html) state that S3 "prevents objects smaller than 128 KB from being transitioned to any storage class" by default. A rule carrying a prefix and nothing else does less than its author expects, and nothing logs an error. The same silence hides [multipart parts that are billed as storage](/blog/incomplete-multipart-storage-leak): the API did exactly what it was told.

**The older configuration that still moves them.** Before September 2024 the default allowed small objects to transition, but only to Glacier Flexible Retrieval and Deep Archive. Configurations created before the change keep that behaviour until they are edited — "if you create, edit, or delete rules, the default transition behavior for your configuration changes" — so two buckets with identical-looking rules can behave differently depending on when they were written.

**The PUT that never meets a filter.** A lifecycle rule filters objects already in Standard. An application writing with `x-amz-storage-class: STANDARD_IA` puts an 8 KB file into the class directly, and the minimum applies from the first month. No filter is involved, because no transition happened.

**The Glacier overhead nobody counts.** Each object transitioned to Glacier Flexible Retrieval or Deep Archive carries 40 KB of extra storage — 8 KB of metadata at Standard rates, 32 KB at the destination rate — billed from the day the rule is satisfied even if the physical move has not finished. For an 8 KB object that is five times its own size, at the more expensive of the two rates.

**The payback nobody calculated.** A 128 KiB object repays its transition request in 7.80 months; a 1 MiB object in 0.98. Below 128 KB it repays nothing, because there is no saving to repay it with. Add the 30-day minimum — an object leaving Standard-IA early is charged for the full 30 days at $0.0125/GB-month — and a rule over churning data can cost more than the class it left. Storage is not the only lever: [in most S3 bills the egress line decides](/blog/s3-total-cost-of-ownership).

## Doing it right

**1. Measure the distribution before writing the rule.** An average hides everything here. Count objects and bytes under 128 KB per prefix, and page the listing properly.

```python
import boto3

s3 = boto3.client("s3")
small = total = small_bytes = 0
kw = {"Bucket": "logs-prod", "Prefix": "events/"}
while True:
    page = s3.list_objects_v2(**kw)
    for o in page.get("Contents", []):
        total += 1
        if o["Size"] < 131072:
            small += 1
            small_bytes += o["Size"]
    if not page.get("IsTruncated"):
        break
    kw["ContinuationToken"] = page["NextContinuationToken"]
print(f"{small:,} of {total:,} under 128 KB, {small_bytes / 2**30:.2f} GiB")
```

**2. Put the intent in the configuration.** State the boundary even when the default agrees with it. `ObjectSizeGreaterThan` and `ObjectSizeLessThan` exclude their own value, so 131072 is the first size included.

```json
{"Rules": [{
  "ID": "events-to-ia",
  "Status": "Enabled",
  "Filter": {"And": {"Prefix": "events/", "ObjectSizeGreaterThan": 131072}},
  "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]
}]}
```

```bash
aws s3api put-bucket-lifecycle-configuration --bucket logs-prod \
  --lifecycle-configuration file://lifecycle.json
```

**3. Leave the small objects in Standard.** No class is cheaper for an 8 KB file: every option either bills 128 KB or offers no tier at all. The saving has to come from the object count, which means batching writes into megabyte-scale objects upstream.

**4. Use Intelligent-Tiering when the mix is unknown.** Free for the small objects, automatic for the large ones, no minimum duration, no retrieval fee, and one transition price instead of a rule per access pattern. It is not a cost reduction for a prefix that is entirely small files.

**5. Watch the small-object usage type.** After the first month in Standard-IA, look for its line on the bill. If it appears, the rule is moving objects it should not touch.

**6. Prove it with a canary.** Write a 64 KB object and a 1 MB object into the prefix, then read `StorageClass` back after the transition day. The console says enabled either way.

## How S3 Explorer fits

The size distribution is the whole decision, and it is easier to see than to script: S3 Explorer's bucket list and folder navigation show each file with its size and date, so a prefix that is nothing but 8 KB fragments is visible before anyone writes a rule. The **Versions** tab makes the second count obvious — every version is another object for the minimum charge — and **test connection** reports how many buckets the credentials actually reach before a profile is saved, while the provider picker's 25 presets keep an AWS bucket and a self-hosted endpoint in the same window. The storage and egress prices behind this arithmetic, side by side with R2, B2 and Wasabi, are in [the S3 pricing comparison guide](https://s3explorer.accessdevops.com/guides/s3-storage-pricing-comparison/?utm_source=blog&utm_medium=in_article&utm_campaign=intelligent-tiering-128kb-rule).

## Checklist

- [ ] The median and the 90th percentile object size of the prefix are known, not just the average.
- [ ] Every transition rule states its size boundary explicitly, even when the default agrees.
- [ ] No rule moves objects below 128 KB into Standard-IA, One Zone-IA or Glacier Instant Retrieval.
- [ ] No application writes small objects with `x-amz-storage-class: STANDARD_IA` at PUT time.
- [ ] Lifecycle configurations written before September 2024 have been read, and the behaviour change on edit is understood.
- [ ] The first bill after a transition is checked for a separate small-object line.
- [ ] In a versioned bucket, every version has been counted as an object for the minimum charge.
- [ ] The transition request fee has been compared with the monthly saving at the real object size.

## Sources

- [Amazon S3 FAQs](https://aws.amazon.com/s3/faqs/), read 27 November 2026: Standard-IA "minimum object storage charge of 128KB" with the 6 KB worked example; Intelligent-Tiering "no minimum billable object size, but objects smaller than 128KB are not eligible for auto-tiering … with no monitoring and automation charge".
- [Understanding and managing Amazon S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html): the comparison table giving 128 KB as the minimum billable object size for Standard-IA, One Zone-IA and Glacier Instant Retrieval, the 30-day and 90-day minimum durations, and the note that objects under 128 KB stay in the Intelligent-Tiering Frequent Access tier.
- [Transitioning objects using Amazon S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html): the September 2024 default, the previous default limited to Glacier Flexible Retrieval and Deep Archive, and the 40 KB per-object archive overhead.
- [Lifecycle configuration elements](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html): `ObjectSizeGreaterThan`, `ObjectSizeLessThan`, and the rule that both exclude their own value.
- [Amazon S3 offer file, us-east-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json), publication date 2026-11-25, offer version `20261125152611`: $0.023 S3 Standard, $0.0125 Standard-IA, $0.01 One Zone-IA, $0.004 Glacier Instant Retrieval, $0.023 Intelligent-Tiering Frequent Access, $0.0025 per 1,000 objects monitoring, $0.01 per 1,000 transitions into Standard-IA, $0.01 per GB Standard-IA retrieval.
- Computed 27 November 2026 with `scripts/tiering-cost-model.py` in this repository; the diagram is generated by `scripts/tiering-diagram.py`.
