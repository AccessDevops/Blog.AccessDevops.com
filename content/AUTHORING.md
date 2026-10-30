# Authoring rules — one S3 article per day

These rules exist so that 100 consecutive articles read like one publication.
Follow them literally. `scripts/next-topic.py` gives you the topic; do not pick
a different one and do not reorder.

## Who reads this

Every article serves three readers at once, in this order:

1. **The non-technical decision maker** — needs to understand the risk and the
   cost in the first 15 seconds. Gets the TL;DR and the "what it costs" line.
2. **The sysadmin / platform engineer** — needs the exact mechanism, the error
   string, the command, the limit. Gets the body.
3. **The architect / buyer** — needs the trade-off and the checklist. Gets the
   last two sections.

If a sentence only serves you, delete it.

## Structure (in this order, headings exactly these)

```
---
title: "<= 65 chars before the em dash"
description: "70-165 chars, plain language, no clickbait"
date: YYYY-MM-DD
author: "Clement Baranger"
tags: [3-5 lowercase tags]
---

## The short version

- 3 to 5 bullets. No jargon that a product owner would not know.
- Each bullet is a fact, not a promise.
- One bullet states the cost or the risk in money or hours.

## What actually happens

The mechanism, with numbers. 2-4 paragraphs.

![<alt text that describes the diagram>](/diagrams/<slug>.svg)

## Where it bites

The failure modes, the error strings, the wrong assumption. Use a table or a
bullet list when comparing more than two variants.

## Doing it right

The procedure. Commands in a fenced block with the language tag. Copy-pasteable,
with real values. 3-6 steps.

## How S3 Explorer fits

2-4 sentences, specific. Name the screen or capability. Never claim a feature the
product does not have. Link once: [S3 Explorer](https://s3explorer.accessdevops.com).
No superlatives, no "revolutionary", no "game-changing".

## Checklist

5-8 checkboxes. Each one is verifiable by someone who is not you.
```

## Numbers and sources

- Every price, limit or quota must be either **cited** (link to the vendor page)
  or explicitly labelled as a worked example (`at $0.023/GB, 10 TB costs…`).
- Never invent a benchmark. If you did not measure it, say "vendor-published"
  or omit it.
- Dollar figures: state the region and the date of the price snapshot.

## Visuals

- **One SVG diagram minimum**, at `public/diagrams/<slug>.svg`, hand-authored,
  viewBox set, no external fonts (use `font-family="Inter, system-ui, sans-serif"`).
  Palette: `#020817` ink, `#2563EB` accent, `#94A3B8` muted, `#E2E8F0` rule —
  the blog's tokens. Flat fills, 1px strokes, no gradients, no drop shadows.
- Reference it with `![alt](/diagrams/<slug>.svg)`.
- A real screenshot from `public/screenshots/` is allowed **only** when it shows
  the exact screen being discussed. Never reuse one to illustrate something else.
- Under 60 KB per SVG.

## Voice

- English, British spelling (`organisation`, `behaviour`), except in product names.
- Short sentences. Active voice. No rhetorical questions as headings.
- Banned openings: "In today's cloud landscape", "As we all know", "Let's dive in".
- Banned words: seamless, robust, leverage (as a verb), unleash, empower, cutting-edge.
- Never write "it's important to note". Say the thing.
- Em dashes are fine; emoji are not.

## SEO / GEO

- `title` must contain the query people actually type.
- `description` answers the question in one sentence.
- One `<h1>`, sections are `<h2>`; never skip a level.
- Internal links: at least one link to another article in the series using the
  slug of a written topic.
- After writing, add the article to the `## Articles` list in `public/llms.txt`
  (newest first, one line, verb-first summary).

## Ship it

```bash
npm run generate
python3 scripts/seo-audit.py   # must exit 0
git add -A
git commit -m "Article: <slug>"
git push origin main
```

The push triggers the Netlify build. If the audit fails, fix the article — do
not weaken the check.
