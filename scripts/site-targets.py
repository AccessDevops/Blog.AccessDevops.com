#!/usr/bin/env python3
"""Choisit la page du site produit qui correspond à un article, et vérifie le lien publié.

Le blog et le site produit sont deux sites distincts. Un article qui renvoie vers
l'accueil du site produit n'aide ni le lecteur — qui vient de lire sur un sujet précis —
ni le référencement, puisque c'est la page profonde qui se fait indexer.

Ce script lit la sitemap du site produit, en tire le titre et la description réels de
chaque page, et classe les pages par recouvrement avec les mots de l'article. Il ne
devine rien : tout ce qu'il affiche vient de la sitemap ou du HTML servi.

    python3 scripts/site-targets.py --for repairing-multipart-uploads-etags \
        --tags uploads,etag --top 5
    python3 scripts/site-targets.py --check content/blog/<slug>.md

`--check` sort en erreur quand l'article ne contient aucun lien profond : c'est le
garde-fou qui empêche la régression vers un lien d'accueil.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SITE = "https://s3explorer.accessdevops.com"
ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "site-targets.json"
GUIDES_TS = ROOT / "lib" / "guide-links.ts"
PRODUCT_HOST = "s3explorer.accessdevops.com"

STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "or", "for", "with", "your",
        "how", "why", "what", "when", "is", "are", "do", "does", "it", "its", "you",
        "from", "by", "at", "as", "that", "this", "be", "not", "no", "de", "la", "le"}

# Mots présents dans presque toutes les pages : ils ne désignent aucun sujet et font
# gagner une page au hasard. « cloud » rapproche un article de Clever Cloud par accident.
GENERIC = {"cloud", "s3", "storage", "file", "files", "object", "objects", "data",
           "client", "desktop", "bucket", "buckets", "api", "browser", "guide", "guides"}

# Vocabulaire du produit : l'article dit « coût », la page dit « pricing ». Sans cette
# table, un article sur le coût total ne rejoint jamais la page des prix.
SYNONYMS = {
    "cost": "pricing", "costs": "pricing", "price": "pricing", "prices": "pricing",
    "tco": "pricing", "bill": "pricing", "billing": "pricing", "egress": "pricing",
    "preview": "preview", "previews": "preview", "viewer": "viewer", "view": "viewer",
    "uploads": "multipart", "upload": "multipart", "etag": "multipart", "parts": "multipart",
    "presign": "presigned", "presigned": "presigned", "signed": "presigned",
    "errors": "error", "signaturedoesnotmatch": "error", "denied": "error",
    "thumbs": "preview", "thumbnail": "preview", "thumbnails": "preview",
}


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in raw if len(t) > 2 and t not in STOP}


def fetch_pages() -> dict[str, dict]:
    """Sitemap → {path: {title, description}}. Mis en cache, la sitemap bouge peu."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    xml = urllib.request.urlopen(f"{SITE}/sitemap.xml", timeout=25).read().decode()
    paths = [loc.replace(SITE, "") for loc in re.findall(r"<loc>([^<]+)</loc>", xml)]

    def one(path: str) -> tuple[str, dict]:
        try:
            html = urllib.request.urlopen(SITE + path, timeout=25).read().decode("utf-8", "replace")
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            desc = re.search(r'<meta\s+name="description"\s+content="(.*?)"', html, re.S)
            return path, {
                "title": (title.group(1).strip() if title else ""),
                "description": (desc.group(1).strip() if desc else ""),
            }
        except Exception as exc:  # une page injoignable ne doit pas casser le choix
            return path, {"title": "", "description": f"(illisible : {exc})"}

    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = dict(pool.map(one, paths))
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    return pages


def guide_keys() -> dict[str, str]:
    """path → clé `guide:` déclarée dans lib/guide-links.ts."""
    if not GUIDES_TS.exists():
        return {}
    src = GUIDES_TS.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for m in re.finditer(r"'([\w-]+)':\s*\{(.*?)\n  \}", src, re.S):
        key, body = m.group(1), m.group(2)
        path = re.search(r"path:\s*'([^']+)'", body)
        slug = re.search(r"slug:\s*'([^']+)'", body)
        if path:
            out[path.group(1)] = key
        elif slug:
            out[f"/guides/{slug.group(1)}/"] = key
    return out


EXCLUDE = {"/", "/about/", "/buy/", "/privacy/", "/terms/",
           "/guides/", "/providers/", "/news/", "/security/"}


def rank(pages: dict[str, dict], keys: dict[str, str], query: str, top: int) -> list[tuple]:
    want = {SYNONYMS.get(t, t) for t in tokens(query) if t not in GENERIC}
    candidates = {p: m for p, m in pages.items() if p not in EXCLUDE}
    # Un mot présent dans presque toutes les pages ne distingue rien : « s3 » est dans
    # tous les chemins, « cloud » dans la moitié des descriptions. Les garder fait
    # gagner une page fournisseur sur un mot de tag, ce qui est un faux rapprochement.
    df: dict[str, int] = {}
    for path, meta in candidates.items():
        for t in tokens(path + " " + meta.get("title", "")):
            df[t] = df.get(t, 0) + 1
    cutoff = max(2, len(candidates) // 2)
    want = {t for t in want if df.get(t, 0) <= cutoff}

    scored = []
    for path, meta in candidates.items():
        path_hits = want & tokens(path)
        title_hits = want & tokens(meta.get("title", ""))
        desc_hits = want & tokens(meta.get("description", ""))
        # Le chemin décrit le sujet de la page ; un titre le précise ; une description
        # parle souvent du voisin et produit des rapprochements faux. Un mot commun dans
        # une description ne suffit donc pas : sans recoupement de chemin ni de titre,
        # la page est écartée.
        score = 3 * len(path_hits) + 2 * len(title_hits) + len(desc_hits)
        if not path_hits and not title_hits:
            continue
        if score < 4:
            continue
        scored.append((score, path, keys.get(path), meta.get("title", ""),
                       path_hits | title_hits | desc_hits))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return scored[:top]


def check(article: pathlib.Path) -> int:
    text = article.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    deep = re.findall(rf"https://{re.escape(PRODUCT_HOST)}/([^)\s\"'>]+)", body)
    roots = [p for p in deep if p.strip("/") == ""]
    others = [p for p in deep if p.strip("/") != ""]
    fm = re.search(r"^---\n(.*?)\n---", text, re.S)
    guide = re.search(r"^guide:\s*(\S+)\s*$", fm.group(1), re.M) if fm else None

    problems = []
    if not deep:
        problems.append("aucun lien vers le site produit")
    elif not others:
        problems.append(f"seul lien produit : l'accueil ({len(roots)} occurrence(s))")
    if guide and guide.group(1).strip("'\"") not in guide_keys().values():
        problems.append(f"clé `guide: {guide.group(1)}` absente de lib/guide-links.ts")
    if not guide:
        problems.append("frontmatter sans `guide:` : aucune carte vers une page profonde")

    if problems:
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    print(f"  ✓ lien profond : {others[0]}  ·  carte : guide: {guide.group(1)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--for", dest="query", help="slug, titre ou mots-clés de l'article")
    ap.add_argument("--tags", default="", help="tags de l'article, séparés par des virgules")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--check", type=pathlib.Path, help="vérifie un article avant publication")
    ap.add_argument("--refresh", action="store_true", help="ignore le cache de la sitemap")
    args = ap.parse_args()

    if args.refresh and CACHE.exists():
        CACHE.unlink()

    if args.check:
        return check(args.check)

    pages = fetch_pages()
    keys = guide_keys()
    query = f"{args.query or ''} {args.tags.replace(',', ' ')}".strip()
    if not query:
        for path, meta in sorted(pages.items()):
            print(f"  {path:<52} {keys.get(path, '—'):<34} {meta.get('title','')[:60]}")
        return 0

    hits = rank(pages, keys, query, args.top)
    if not hits:
        print("  aucun recoupement : prends la page la plus proche dans --list, ou l'accueil "
              "du site produit en le justifiant dans l'article", file=sys.stderr)
        return 1
    print(f"  pour « {query} » :")
    for score, path, key, title, overlap in hits:
        print(f"  {score:>2}  {path:<50} guide: {key or '—'}")
        print(f"      {title[:90]}")
        print(f"      mots communs : {', '.join(sorted(overlap))[:90]}")
    print("\n  Choisis le premier dont le sujet correspond vraiment ; le score classe, il ne décide pas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
