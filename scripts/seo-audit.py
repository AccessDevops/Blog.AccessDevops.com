#!/usr/bin/env python3
"""SEO/GEO gate for every article. Run after `npm run generate`.

Checks each content/blog/*.md against its built page plus sitemap/rss.
Exit code 1 if any article fails a hard check.
"""
import os, re, sys, glob, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://blog.accessdevops.com"
DIST = os.path.join(ROOT, "dist")
CONTENT = os.path.join(ROOT, "content", "blog")

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    fm = {}
    if not m:
        return fm, text
    for line in m.group(1).split("\n"):
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            v = v.strip().strip('"').strip("'")
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            fm[k.strip()] = v
    return fm, text[m.end():]

def words(md):
    body = re.sub(r"<[^>]+>", " ", md)
    body = re.sub(r"[#*`>|\-]", " ", body)
    return len(body.split())

def one(pattern, text, flags=re.S):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

sitemap = open(os.path.join(DIST, "sitemap.xml"), encoding="utf-8").read()
rss = open(os.path.join(DIST, "rss.xml"), encoding="utf-8").read()

rows, failures = [], 0
for path in sorted(glob.glob(os.path.join(CONTENT, "*.md"))):
    slug = os.path.splitext(os.path.basename(path))[0]
    fm, body = frontmatter(open(path, encoding="utf-8").read())
    page = os.path.join(DIST, "blog", slug + ".html")
    if not os.path.exists(page):
        rows.append((slug, "FAIL", "page not built")); failures += 1; continue
    h = open(page, encoding="utf-8").read()
    url = f"{SITE}/blog/{slug}"

    checks = []
    def chk(ok, label, detail=""):
        checks.append((bool(ok), label, detail))

    title = html.unescape(one(r"<title>(.*?)</title>", h) or "")
    desc = one(r'<meta name="description" content="([^"]*)"', h) or ""
    canon = one(r'<link rel="canonical" href="([^"]*)"', h)
    h1 = len(re.findall(r"<h1[\s>]", h))
    lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
    ld = " ".join(lds)

    chk(30 <= len(title.split("—")[0].strip()) <= 65, "title length", f"{len(title)} car.")
    chk(70 <= len(desc) <= 165, "meta description", f"{len(desc)} car.")
    chk(canon == url, "canonical self-ref", canon or "absent")
    chk(h1 == 1, "single h1", f"{h1}")
    chk('property="og:image"' in h, "og:image")
    chk('name="twitter:card"' in h, "twitter:card")
    chk('"@type":"BlogPosting"' in ld, "BlogPosting JSON-LD")
    chk('"@type":"BreadcrumbList"' in ld, "BreadcrumbList JSON-LD")
    chk(url in sitemap, "in sitemap")
    chk(slug in rss, "in rss")
    chk(words(body) >= 600, "word count", f"{words(body)}")
    if words(body) < 600:
        checks[-1] = (True, "word count (warning)", f"{words(body)} mots")  # soft: short announcement posts are legitimate
    imgs = re.findall(r"<img\s[^>]*>", h)
    chk(all("alt=" in i for i in imgs), "img alt", f"{len(imgs)} img")
    if fm.get("video"):
        chk('"@type":"VideoObject"' in ld, "VideoObject JSON-LD")
        chk('property="og:video"' in h, "og:video")

    bad = [c for c in checks if not c[0]]
    failures += len(bad)
    status = "PASS" if not bad else f"FAIL ({len(bad)})"
    rows.append((slug, status, ", ".join(c[1] for c in bad)))

print(f"{'ARTICLE':<38} {'STATUS':<10} ISSUES")
print("-" * 96)
for slug, status, detail in rows:
    print(f"{slug:<38} {status:<10} {detail}")

print("-" * 96)
print(f"{len(rows)} articles · {failures} failed checks")
sys.exit(1 if failures else 0)
