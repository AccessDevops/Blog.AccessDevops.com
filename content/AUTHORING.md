# Authoring rules — three S3 articles per week

Single source of truth for the series. `content/topics.json` holds the 100 topics;
this file holds everything else. Follow it literally — it exists so that every
article reads like the same publication and none of them ships a factual error.

The cadence changed on 2026-11-03, deliberately. One article per day on a domain
opened days earlier, with 100 topics queued in advance, is the profile Google's
scaled-content policy is written to catch — the writing can be sound and the
cadence is still assessed on its own. Two or three a week is the pace of a
publication with something to say, not of a pipeline.

## Choosing the topic

The queue is not an order. Each time, pick from the unwritten topics:

```bash
python3 scripts/next-topic.py --list      # every remaining topic + the tags it would grow
```

Choose on these criteria, in this order:

1. **What readers already read.** Articles that produced `blog_read_complete`
   and, above all, `blog_product_click` with `placement: "in_article"` tell you
   which neighbourhood works. A topic next to one that converts beats a topic at
   the head of the list.
2. **What is searched and not answered.** Queries where the product site is seen
   but never clicked (`s3 explorer`, `s3 bucket explorer`) are demand without a
   page. An article can claim them; a comparison page usually converts better,
   so decide which one the query deserves.
3. **Which tag is one article short.** A tag page becomes indexable at
   `MIN_POSTS_FOR_INDEX` (lib/tags.ts, currently 2). Picking a topic that pushes
   a tag over the threshold creates a second indexable page for free.

Write the criterion in the commit body — one sentence, why this topic now:

```
Article: <slug>

Chosen for criterion 2: the product site is seen for "s3 bucket explorer" with
0 clicks, and no page claims it.
```

If the data is not reachable (no PostHog key in the environment, no Search
Console export), say so in the commit and in the final message, and fall back to
criterion 3, which needs nothing but the repository. Do not invent numbers to
justify a choice.

## What makes an article publishable

Every article must contain **at least one thing that could not have been written
without doing the work**. One of:

- a measurement you made yourself, with the command that reproduces it;
- a real error, pasted as it came out, unedited;
- a screenshot of S3 Explorer showing the case — ask Clément, you cannot launch
  the app yourself;
- a comparison table whose figures are dated and sourced;
- a diagram in `public/diagrams/`.

The SVG is the floor, not the ceiling: it is expected. If the only unique element
an article can offer is a generic diagram, write a different topic this week and
come back to this one when you can measure something.

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
npm run og                            # per-article Open Graph image — not optional
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

**IndexNow runs by itself after the deploy.** Do not call `npm run indexnow`
after an article: the deploy already pings it, and a second submission of the
same URLs is noise.

## Every third article: measure, then say what you found

After three articles, read PostHog for the period and report four things:

- visitors and articles seen (`blog_article_viewed`);
- completion rate per article (`blog_read_complete` / `blog_article_viewed`);
- clicks to the product, split by `placement` (`in_article`, `guide_card`, `nav`,
  `footer`);
- source split, keeping `ai_assistant` apart from the search engines.

Two readings decide the next change:

- **Many views, few completions** → the title or the opening is wrong, not the
  topic. Rewrite the lede before writing another article on that theme.
- **Read to the end, no product click** → the guide link is in the wrong place,
  or the guide does not match the article. Fix `lib/guide-links.ts` or move the
  link to where the problem is actually described.

If PostHog cannot be queried, say so plainly. A measurement you do not have is
not a measurement of zero.

## Failure handling

- Audit fails → fix the article, re-run. Never weaken `scripts/seo-audit.py`.
- Build fails → read the real error, fix it, re-run. Do not push a broken `dist`.
- Push fails → report the failure verbatim. Do not retry blindly more than twice.
- Topic queue exhausted (`next-topic.py` exits 3) → say so and stop.
- If you cannot source a number, write the article without it. A missing figure is
  better than an invented one.
