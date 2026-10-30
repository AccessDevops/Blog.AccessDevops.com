---
title: "S3 Explorer in practice: from a blank screen to browsing a bucket in five minutes"
description: "A step-by-step walkthrough of S3 Explorer against a local S3 endpoint: pick a provider, test the connection, browse buckets, preview objects, inspect metadata and read the request metrics dashboard. Every screenshot comes from a real session."
date: 2026-10-30
author: "Clement Baranger"
tags: ["s3", "tutorial", "tooling", "seaweedfs"]
video: "/videos/s3explorer-teaser.mp4"
videoPoster: "/videos/s3-explorer-teaser-poster.webp"
videoDuration: "PT30S"
---

<figure class="clip">
  <video controls playsinline preload="metadata" poster="/videos/s3-explorer-teaser-poster.webp" width="1080" height="1920" style="width:100%;height:auto;border-radius:16px;background:#0B0F0E;display:block">
    <source src="/videos/s3explorer-teaser.mp4" type="video/mp4">
    Your browser does not support embedded video.
  </video>
  <figcaption>30 seconds, no voiceover — from pick-provider to request-metrics dashboard. Every frame is a real capture of the session below.</figcaption>
</figure>

Most S3 clients assume you already know your endpoint format, your addressing mode and which fields are optional. S3 Explorer takes the opposite route: you pick your provider from a list, and the connection form configures itself.

This walkthrough shows the whole path — installation to first object — on a real session. The endpoint is a local **SeaweedFS** gateway (not an AWS account), because that keeps the demo reproducible and free. Nothing changes for AWS, R2, B2 or Wasabi: only the provider tile you click.

## Step 1 — Pick a provider

Open the app and hit **+ Add**. Before showing you a single field, it asks which provider you are connecting to.

<figure>
  <img src="/screenshots/01-provider-picker.webp" alt="S3 Explorer provider picker with 25 presets, filter tabs for Cloud, Specialist, Self-hosted and Enterprise" width="1200" height="804" loading="lazy">
  <figcaption>25 presets, filtered by category. Custom/Other is there for anything not listed.</figcaption>
</figure>

Twenty-five providers ship with the app, grouped into Cloud, Specialist, Self-hosted and Enterprise. The first tile — **Custom / Other** — is the escape hatch for private endpoints.

## Step 2 — The form configures itself

Pick **SeaweedFS** and the form arrives pre-filled with the endpoint format, the default port and the addressing mode that provider requires.

<figure>
  <img src="/screenshots/02-connection-form.webp" alt="Connection form pre-configured for SeaweedFS with endpoint URL, region, credentials and path-style addressing" width="1200" height="804" loading="lazy">
  <figcaption>Provider chosen: the endpoint format, the default region and path-style addressing are already set.</figcaption>
</figure>

Two details worth noting, because they are where most S3 connections fail:

- **Force path-style addressing** is already ticked, with the note *"required for SeaweedFS"*. Bucket-in-hostname addressing (`bucket.endpoint`) breaks on most self-hosted gateways.
- **Anonymous connection** is a separate, explicit toggle — read-only access for public buckets, no credentials stored.

The provider context also carries documentation: *Endpoint Format*, *Where to Find Credentials* and *Tips & Notes* expand inline, so you don't leave the app to read a wiki.

## Step 3 — Test before you save

**Test Connection** runs the real call — it does not just ping the host.

<figure>
  <img src="/screenshots/03-test-success.webp" alt="Successful connection test showing Found 3 buckets before saving the profile" width="1200" height="804" loading="lazy">
  <figcaption>Successfully connected. Found 3 buckets.</figcaption>
</figure>

The message tells you what actually happened: *"Successfully connected. Found 3 buckets."* A wrong key, a wrong region or a blocked ListBuckets call each produce a different failure — and you find out here, not after saving a broken profile.

## Step 4 — Buckets land in the sidebar

Save, and the connection shows up on the left with its buckets underneath.

<figure>
  <img src="/screenshots/04-buckets.webp" alt="Sidebar listing the SeaweedFS connection and three buckets under it" width="1200" height="804" loading="lazy">
  <figcaption>One connection, three buckets, loaded on selection.</figcaption>
</figure>

The sidebar keeps connections and buckets in one tree, so switching between two accounts is a click rather than a dialog. Each bucket shows its size and object count once loaded — here `863.85 KB · 18 objects`.

## Step 5 — Browse

Open a bucket and you get a plain table: name, size, last modified.

<figure>
  <img src="/screenshots/05-file-list.webp" alt="File listing of the 2026-10 prefix showing 14 JPEG objects with sizes and modified dates" width="1200" height="804" loading="lazy">
  <figcaption>14 objects in a prefix, with the running totals in the footer.</figcaption>
</figure>

The footer keeps a running total — *14 items (0 Folders, 14 Files)* and *841.99 KB* — which is the number you actually need when you are deciding whether a prefix is worth moving. Folders are prefixes, and double-clicking opens them like directories, without a re-listing round-trip.

## Step 6 — Look inside an object

Double-click a file and it opens in a tabbed viewer.

<figure>
  <img src="/screenshots/06-image-preview.webp" alt="Object preview modal with Content, Metadata, Versions, Permissions, Tags, Headers and Event Log tabs" width="1200" height="804" loading="lazy">
  <figcaption>Content tab with inline image preview, plus six more tabs for the object's other faces.</figcaption>
</figure>

Seven tabs per object: **Content**, **Metadata**, **Versions**, **Permissions**, **Tags**, **Headers**, **Event Log**. Images preview inline, text is editable, and nothing requires downloading the file first.

## Step 7 — Read the metadata

The Metadata tab is the one you end up using at 2am when something is wrong.

<figure>
  <img src="/screenshots/07-metadata.webp" alt="Metadata tab showing object key, size, last modified date, storage class STANDARD and ETag" width="1200" height="804" loading="lazy">
  <figcaption>Key, size, timestamp, storage class and ETag — the five fields that explain most object-level bugs.</figcaption>
</figure>

Key, size, last modified, **storage class** and **ETag**. That ETag is an MD5 for a single-part upload, which means it doubles as a integrity check: compare it with the local file hash and you know instantly whether the upload was corrupted.

## Step 8 — See what the browsing costs

Every request the app makes is recorded locally. The chart icon at the bottom of the sidebar opens the dashboard.

<figure>
  <img src="/screenshots/08-metrics.webp" alt="S3 request metrics dashboard showing 18 requests, cost, requests by category and per-operation timings" width="1200" height="804" loading="lazy">
  <figcaption>18 requests from the session above, broken down by category and by operation, with average latency.</figcaption>
</figure>

This is the part that changes how you use an S3 client. Browsing a bucket is not free:

- **18 requests** for the session above, split **8 LIST / 10 GET**.
- Per-operation latency: `ListBuckets` 23 ms, `ListObjectsV2` 12 ms, `ListMultipartUploads` 8 ms, `GetBucketAcl` 5 ms.
- **Index Efficiency** counts the listings the local index answered instead of re-querying the bucket — 2 saved here.
- A cost estimate and a monthly projection, priced from the provider's published request rates.

At 18 requests the money is invisible. At 500,000 a month, the LIST/GET split *is* your bill — and this is the only client we know of that shows it while you work.

## What this walkthrough leaves out

Two honest caveats. This session ran against SeaweedFS on `127.0.0.1`, so latency numbers reflect a loopback interface, not the internet. And the demo account holds 30 objects — the index efficiency metric only gets interesting at millions, which is precisely the case it was built for.

Everything else — the presets, the pre-filled form, the test step, the tabs, the metrics — behaves exactly as it would against AWS.

> **Try it against your own buckets.** 25 providers, a read-only key is enough for everything shown above. [Download S3 Explorer →](https://s3explorer.accessdevops.com/)
