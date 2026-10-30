# Authoring rules — one S3 article per day

Single source of truth for the daily series. `scripts/next-topic.py` gives you the
topic; this file gives you everything else. Follow it literally — it exists so that
100 consecutive articles read like one publication and none of them ships a
factual error.

## Who reads this

Every article serves three readers at once, in this order:

1. **The non-technical decision maker.** Needs the risk and the cost in the first
   15 seconds. Gets the TL;DR and the money/hours line.
2. **The sysadmin / platform engineer.** Needs the mechanism, the error string, the
   command, the hard limit. Gets the body.
3. **The architect / buyer.** Needs the trade-off and a checklist they can hand to
   someone else. Gets the last two sections.

If a sentence only serves you, delete it.

## Structure — headings exactly these, in this order

```
---
title: "<= 65 chars before the em dash"
description: "70-165 chars, plain language, no clickbait"
date: YYYY-MM-DD          # today in Europe/Paris: date +%F
author: "Clement Baranger"
tags: [3-5 lowercase tags]
---

## The short version

- 3 to 5 bullets. Understandable by someone who does not know what a bucket is.
- Each bullet is a fact, not a promise.
- One bullet states the cost or the risk in money or hours.

## What actually happens

The mechanism, with numbers. 2-4 paragraphs.

![<alt text describing the diagram>](/diagrams/<slug>.svg)

## Where it bites

The failure modes, the exact error strings, the wrong assumption people make.
Use a table or bullets when comparing more than two variants.

## Doing it right

The procedure. Commands in a fenced block with a language tag, copy-pasteable,
with realistic values. 3-6 steps.

## How S3 Explorer fits

2-4 sentences. Name a real screen or capability (see the locked list below).
Link once: [S3 Explorer](https://s3explorer.accessdevops.com).

## Checklist

5-8 checkboxes, each verifiable by someone who is not you.
```

Target 1100-1700 words.

## Facts: verify before you assert

Every price, limit, default or error string must come from the vendor documentation
during that run, or be explicitly labelled as a worked example. Two rules learned
the hard way:

- **Read what the primitive actually does.** An ACL can never carry a `Deny`; only
  policy documents can. Writing "an explicit deny in an ACL" is a factual error a
  knowledgeable reader spots instantly, and it discredits the rest of the article.
- **Distinguish "S3 does X" from "this provider does X".** AWS behaviour is not the
  S3 API. R2, B2, Wasabi, MinIO and GCS each deviate; say which one you mean.

Cite with a link when the claim is a number. Dollar figures: state region and the
date of the price snapshot. Never invent a benchmark: if you did not measure it,
write "vendor-published" or leave it out.

## Visuals

One SVG diagram minimum, at `public/diagrams/<slug>.svg`.

- `viewBox` set, explicit `width`/`height`, no external fonts — use
  `font-family="Inter, system-ui, sans-serif"` and a mono stack for code strings.
- Palette: `#020817` ink, `#2563EB` accent, `#64748B` muted, `#E2E8F0` rule,
  `#FFFFFF` card. Flat fills, 1px strokes, no gradients, no drop shadows.
- Under 60 KB. It must explain the mechanism, not decorate.
- **Labels must fit.** At 11.5px assume ~5.7px per character. A label starting at
  x=414 on a 940-wide canvas must stay under ~22 characters to leave the right
  column clear at x=560.
- **Verify the render before shipping**: open the built SVG in headless Chrome at
  `--window-size=980,700`, look at the PNG, and check for text crossing into
  another column, a box clipped at the bottom, arrows off-centre. This step caught
  a real overlap that looked fine in the source.

A real screenshot from `public/screenshots/` is allowed **only** when it shows the
exact screen being discussed. Never reuse one to illustrate something else.

## S3 Explorer — locked capability list

Only these are real. Do not invent a feature that is not here.

- Provider picker: 25 presets in four groups (Cloud, Specialist, Self-hosted,
  Enterprise) plus a Custom/Other tile, each filling endpoint, region and
  addressing style.
- Connection form: display name, endpoint, region, path-style toggle, credentials,
  with per-provider defaults pre-filled.
- **Test connection**: validates the credentials and reports how many buckets they
  can actually see, before the profile is saved.
- Bucket list, folder navigation, file listing with sizes and dates.
- Image preview, plus Content / Metadata / Versions tabs per object.
- Per-request metrics dashboard: counts of the API calls the session generated
  (LIST, GET and the rest), computed locally in the app.
- Multiple connection profiles, switchable without leaving the window.
- Desktop application: Windows, macOS, Linux (AppImage on Linux), version 0.3.x.

Do not claim anything about telemetry, licensing, client-side encryption or
server-side features — those are not documented here and must not be asserted.

## Voice

- English, British spelling (`organisation`, `behaviour`), except in product names.
- Short sentences. Active voice. No rhetorical question as a heading.
- Banned openings: "In today's cloud landscape", "As we all know", "Let's dive in".
- Banned words: seamless, robust, leverage (verb), unleash, empower, cutting-edge.
- Never write "it's important to note". Say the thing.
- Em dashes are fine. Emoji are not.

## SEO gate

Automatic on build — do nothing: `sitemap.xml`, `rss.xml`, canonical, `og:*`,
`twitter:*`, `BlogPosting` + `BreadcrumbList` JSON-LD.

You must do manually:

- Add the article to the `## Articles` list in `public/llms.txt`, newest first:
  `- [Title](https://blog.accessdevops.com/blog/<slug>): verb-first summary.`
- Add at least one internal link in the body to an already-published article
  (list `content/blog/` for existing slugs).

`python3 scripts/seo-audit.py` enforces, per article: title 30-65 chars,
description 70-165 chars, self-referencing canonical, exactly one `<h1>`,
`og:image`, `twitter:card`, both JSON-LD types, presence in sitemap **and** rss,
alt text on every image. It must exit 0.

## Ship it

```bash
cd /home/hermes/.hermes/cache/scratch/blog-nuxt
npm run generate
python3 scripts/seo-audit.py          # must exit 0 — fix the article, never the script

TOKEN=$(grep -E '^BLOG_GITHUB_TOKEN=' /home/hermes/.hermes/.env | cut -d= -f2- | tr -d "\"' ")
git add -A
git commit -m "Article: <slug>"
git push "https://x-access-token:${TOKEN}@github.com/Accessdevops/Blog.AccessDevops.com.git" main
```

**`git push origin main` does not work here** — the `origin` remote stores no
credentials and the push fails with "could not read Username". Always use the URL
form above. Never echo the token.

Confirm the page is live (the Netlify build takes one to two minutes):

```bash
curl -s -o /dev/null -w '%{http_code}' https://blog.accessdevops.com/blog/<slug>
```

Retry for up to 5 minutes. If it never returns 200, say so in the final message
instead of claiming success.

## Failure handling

- Audit fails → fix the article, re-run. Never weaken `scripts/seo-audit.py`.
- Build fails → read the real error, fix it, re-run. Do not push a broken `dist`.
- Push fails → report the failure verbatim. Do not retry blindly more than twice.
- Topic queue exhausted (`next-topic.py` exits 3) → say so and stop.
- If you cannot source a number, write the article without it. A missing figure is
  better than an invented one.
