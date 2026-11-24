---
title: "Four S3 public access switches, and one that outranks the rest"
description: "What each S3 Block Public Access setting blocks, why the account level beats the bucket, and what two local S3 servers do with the same four flags."
date: 2026-11-23
author: "Clement Baranger"
tags: ["s3", "security", "public-access"]
guide: s3-error-codes
related: [anonymous-read-exact-leak-path, bucket-policy-allow-still-denied]
---

## The short version

- A file can be public in a bucket and still refuse every anonymous request: Block Public Access is not a grant, it sits between the grant and the network and answers first.
- There are four settings, not one. Two refuse a public grant **as it is written**; two accept it and **refuse to honour it** at evaluation. The console's "Block all public access" flips all four together, which is why most people never learn which one did the work.
- The settings exist at four levels: organisation, account, bucket, access point. S3 applies the most restrictive combination, so a bucket switch cannot relax what the account enforces; organisation settings are all four or none.
- Removing a switch restores whatever it was hiding. AWS states that the settings "don't alter existing policies or ACLs", so a bucket made public in 2019 and blocked in 2021 is still public underneath.
- The quiet cost is the fourth switch: once any statement makes a policy public, `RestrictPublicBuckets` cuts **all** cross-account access, and the partner's `403` points at nothing in the permission tab.

## What actually happens

Block Public Access is an evaluation gate, not a permission. A bucket policy granting `s3:GetObject` to `Principal: "*"` is a permission; the switch that refuses to serve it is applied afterwards, at request time. That separation is why the two sides disagree in the console, and why [the leak path is worth measuring one grant at a time](/blog/anonymous-read-exact-leak-path) instead of reading a policy document and hoping.

Two of the four act at write time and two at evaluation. That is the distinction that makes them look redundant and behave differently:

- `BlockPublicAcls` fails the write. `PutObjectAcl` and `PutObject` calls carrying a public ACL are refused, and at account level so is `PutBucket` with a public ACL. Existing policies and ACLs stay in place, so you can still audit them.
- `IgnorePublicAcls` lets the write through and ignores the grant. AWS puts the contrast in one line: it blocks public access granted by ACLs "while still allowing PutObject calls that include a public ACL".
- `BlockPublicPolicy` rejects `PutBucketPolicy` when the document allows public access, and it rejects `PutAccessPointPolicy` for the bucket's same-account access points.
- `RestrictPublicBuckets` removes cross-account access from a bucket whose policy is public, keeping only AWS service principals and principals inside the owner account.

![Four Block Public Access settings act at write time or at evaluation time, the most restrictive level of organisation, account, bucket and access point decides the answer, and the stored grant survives every switch](/diagrams/block-public-access-four-switches.svg)

Then the levels. S3 checks the organisation policy, the account setting, the bucket setting and — if the request arrives through one — the access point setting, and applies the most restrictive. A bucket with everything off inside an account with everything on stays protected.

Two details cost people real time. Account-level settings "apply to all AWS Regions globally" but "might not take effect in all Regions immediately or simultaneously", so a bucket created in a newly enabled region a minute later is not reliably covered. And `GetBucketAcl` and `GetObjectAcl` return the **effective** permissions, not the stored ones: with `IgnorePublicAcls` on, the ACL you read back is the one S3 is enforcing. You see a private ACL and conclude the object was never public.

## Where it bites

The four settings in one table, with the level at which each holds:

| Setting | Acts | Stops | Leaves behind |
|---|---|---|---|
| `BlockPublicAcls` | write | public ACL on `PutObjectAcl`, `PutObject`, and `PutBucket` at account level | every ACL already stored |
| `IgnorePublicAcls` | evaluation | nothing at write; the grant is ignored when a request is evaluated | the stored public ACL, and a `GetObjectAcl` that reports it |
| `BlockPublicPolicy` | write | `PutBucketPolicy` documents that allow public access | existing policies, and the ability of a policy to grant `PutPublicAccessBlock` |
| `RestrictPublicBuckets` | evaluation | all cross-account use of a bucket whose policy is public | compatible with a partner integration that shares the bucket |

**`BlockPublicPolicy` per bucket protects very little on its own.** AWS says it plainly: "A bucket policy can allow users to alter a bucket's block public access settings." Whoever can rewrite the policy can grant themselves `s3:PutBucketPublicAccessBlock`, switch it off, then write the public policy. At account level the rejection happens above the bucket and the trick fails.

**`RestrictPublicBuckets` is the one that takes a partner offline.** It blocks "public and cross-account access derived from any public access point or bucket policy, including non-public delegation to specific accounts". A policy with three statements — CloudTrail, one named account and `*` — keeps only CloudTrail, because one public statement subjects the whole bucket to the restriction.

**The exact errors on the way in.** With ACLs disabled by Object Ownership, an ACL write returns `400 AccessControlListNotSupported`: `The bucket does not allow ACLs`. Applying `Bucket owner enforced` to a bucket whose ACL still grants public read fails with `InvalidBucketAclWithObjectOwnership` and `Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting` — move those grants into the policy and reset the ACL first. Since 28 April 2023 new buckets get Block Public Access on and ACLs off by default ([AWS announcement](https://aws.amazon.com/about-aws/whats-new/2023/04/amazon-s3-security-best-practices-buckets-default/)), so this bites on older buckets.

**"S3-compatible" does not mean these switches exist.** I ran the same seven calls against two local implementations on 23 November 2026 with `scripts/bpa-probe.py`, which is in the repository:

```bash
pip install boto3
python3 scripts/bpa-probe.py --endpoint http://127.0.0.1:15000 --label "moto 5.2.6"
python3 scripts/bpa-probe.py --endpoint http://127.0.0.1:18337 --label "SeaweedFS 4.50"
```

```
## moto 5.2.6  (http://127.0.0.1:15000)  2026-11-23

PUT ?publicAccessBlock        ok
GET ?publicAccessBlock        ok
PutObjectAcl public-read      ok
PutBucketPolicy Principal *   ok
anon GET object               200
anon GET listing              200
DELETE ?publicAccessBlock     ok
anon GET after delete         200

## SeaweedFS 4.50  (http://127.0.0.1:18337)  2026-11-23

PUT ?publicAccessBlock        NotImplemented: A header you provided implies functionality that is not implemented
GET ?publicAccessBlock        NotImplemented: A header you provided implies functionality that is not implemented
PutObjectAcl public-read      AccessDenied: Access Denied.
PutBucketPolicy Principal *   ok
anon GET object               200
anon GET listing              200
DELETE ?publicAccessBlock     NotImplemented: A header you provided implies functionality that is not implemented
anon GET after delete         200
```

Two readings. moto stores the configuration and enforces none of it: all four switches on, a public ACL, a public policy, and an unsigned `GET` still returns `200` with the bytes. SeaweedFS does not implement the API at all, and answers `NotImplemented` about a header — a plausible-looking message for an operation that server has never had. Both say the same thing: the four switches are an AWS control-plane feature, not part of the S3 data-plane API, so on MinIO, Ceph, Garage or SeaweedFS the bucket policy is your only gate. The `AccessDenied` on the ACL write closes the point — an implementation refusing ACLs makes `IgnorePublicAcls` meaningless, because there is nothing to ignore.

## Doing it right

**1. Read all four levels before changing anything.** A bucket-level answer is not the answer:

```bash
aws s3api get-public-access-block --bucket warehouse-prod
aws s3api get-public-access-block --account-id 111122223333
aws s3api get-bucket-policy-status --bucket warehouse-prod
```

`NoSuchPublicAccessBlockConfiguration` means the bucket inherits the account's setting. `IsPublic: true` means the stored policy qualifies as public even while a switch neutralises it.

**2. Ask the internet, not the console.**

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://warehouse-prod.s3.eu-west-3.amazonaws.com/payroll.csv
curl -s -o /dev/null -w '%{http_code}\n' 'https://warehouse-prod.s3.eu-west-3.amazonaws.com/?list-type=2'
```

Two `403`s are the only result that means anything; a `200` on either is the finding, whatever the settings page says.

**3. Switch them on at account level first, then leave the buckets alone.**

```bash
aws s3api put-public-access-block \
  --account-id 111122223333 \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**4. Before step 3, find the cross-account statements `RestrictPublicBuckets` will kill.** Any policy with a wildcard principal becomes subject to the restriction wholesale:

```bash
aws s3api get-bucket-policy --bucket warehouse-prod --query Policy --output text \
  | jq -r '.Statement[] | select(.Principal=="*" or .Principal.AWS=="*") | .Sid'
```

If the same document also grants a partner account, that grant dies when the switch goes on. Split it: move the delegation into its own policy, or scope it by `aws:PrincipalArn` and a condition so the document is not public at all.

**5. Remove the ACL door instead of guarding it.** After moving any grant the ACL still carries into the policy, set Object Ownership to `Bucket owner enforced`:

```bash
aws s3api put-bucket-ownership-controls --bucket warehouse-prod \
  --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
```

The ACL channel is then closed at the API, not merely ignored at evaluation, and the two ACL switches become belt and braces.

**6. Re-run step 2 and record the answer with a date.** Region-to-region propagation carries no guarantee of immediacy, so the check belongs after the change, from outside, on the exact URL.

None of this explains the neighbouring failure — a request that should be allowed coming back `AccessDenied` while every policy in sight says Allow. That is [a different chain of gates](/blog/bucket-policy-allow-still-denied), and the four switches are only one of them.

## How S3 Explorer fits

The shortest path to "which credentials can still see this bucket" is a profile carrying exactly those credentials. [S3 Explorer](https://s3explorer.accessdevops.com/guides/s3-error-codes/?utm_source=blog&utm_medium=in_article&utm_campaign=block-public-access-four-switches) keeps several connection profiles side by side, and **Test connection** reports how many buckets a set of credentials can actually see before the profile is saved — a count that drops as soon as `RestrictPublicBuckets` or a scoped policy takes effect. The per-request metrics dashboard then shows the `LIST` and `GET` calls the session generated, so "the console says blocked" and "the client is served" sit in one window.

## Checklist

- [ ] Both account-level and bucket-level settings were read, not just the bucket's
- [ ] An unauthenticated `curl` returns `403` for the object and for the listing
- [ ] Every bucket policy statement with a wildcard principal was listed before `RestrictPublicBuckets` went on
- [ ] Named-account delegations in those policies were tested from the partner side, not assumed
- [ ] Object Ownership is `Bucket owner enforced`, so ACLs cannot come back
- [ ] `get-bucket-policy-status` reports `IsPublic: false`
- [ ] The switches are on at account level, where a bucket policy cannot turn them off
- [ ] The `403` was reproduced after the change and dated, not inferred from the console
