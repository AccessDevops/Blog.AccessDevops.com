#!/usr/bin/env python3
"""Montre, pour un sujet candidat, les articles publiés qui en sont les plus proches.

Un score de similarité ne tranche pas : deux articles peuvent partager tous leurs mots
et traiter deux questions différentes, ou n'en partager presque aucun et raconter la même
chose (c'est le cas de « resuming an interrupted upload » et « the uploads nobody
finished » : 1,8 % de recouvrement textuel, même panne, deux remèdes).

Ce script ne décide donc pas. Il affiche les voisins et leur thèse réelle — le premier
paragraphe de « The short version » — pour que l'auteur du prochain article puisse dire
en une phrase ce qu'il ajoute, ou renoncer au sujet.

    python3 scripts/topic-neighbours.py incomplete-multipart-storage-leak
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOG = ROOT / "content" / "blog"
TOPICS = ROOT / "content" / "topics.json"

STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "or", "for", "with", "your",
        "how", "why", "what", "when", "is", "are", "do", "does", "it", "its", "you",
        "from", "by", "at", "as", "that", "this", "be", "not", "no"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP}


def frontmatter(text: str) -> str:
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def published() -> dict[str, dict]:
    out = {}
    for path in sorted(BLOG.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        title = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M)
        tags = re.search(r"^tags:\s*\[(.*?)\]", fm, re.M)
        date = re.search(r"^date:\s*(\S+)", fm, re.M)
        body = text[len(fm) + 8:] if fm else text
        short = re.search(r"## The short version\s*(.*?)(?=\n## )", body, re.S)
        bullets = []
        if short:
            for line in short.group(1).splitlines():
                line = line.strip()
                if line.startswith(("- ", "* ")) and len(line) > 30:
                    bullets.append(line[2:].strip())
        out[path.stem] = {
            "title": title.group(1) if title else path.stem,
            "tags": [t.strip().strip("'\"") for t in tags.group(1).split(",")] if tags else [],
            "date": date.group(1) if date else "",
            "thesis": bullets[0] if bullets else "",
            "profile": words((title.group(1) if title else "") + " " + (tags.group(1) if tags else "")),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="slug du sujet candidat (ou un mot-clé libre)")
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    pub = published()
    candidate = None
    if TOPICS.exists():
        data = json.loads(TOPICS.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("topics", [])
        candidate = next((t for t in rows if t.get("slug") == args.slug), None)
    probe = words(f"{args.slug.replace('-', ' ')} "
                  f"{candidate.get('title', '') if candidate else ''} "
                  f"{' '.join(candidate.get('tags', [])) if candidate else ''}")

    ranked = []
    for slug, info in pub.items():
        if slug == args.slug:
            continue  # le sujet candidat, s'il est déjà publié, n'est pas son propre voisin
        shared = probe & info["profile"]
        if not shared:
            continue
        score = len(shared)
        ranked.append((score, slug, sorted(shared), info))
    ranked.sort(key=lambda r: (-r[0], r[1]))

    print(f"  sujet : {args.slug}")
    if candidate:
        print(f"  titre : {candidate.get('title', '')}")
        print(f"  angle : {candidate.get('angle', '')[:160]}")
    print(f"  voisins publiés : {len(ranked)} recoupements de vocabulaire\n")

    for score, slug, shared, info in ranked[: args.top]:
        print(f"  {score:>2} mots communs ({', '.join(shared[:6])})")
        print(f"     {slug}  ·  {info['date']}")
        print(f"     « {info['title']} »")
        if info["thesis"]:
            print(f"     thèse : {info['thesis'][:190]}")
        print()

    print("  À toi de trancher : si la thèse d'un voisin répond déjà à la question que le")
    print("  sujet pose, ce n'est pas un nouvel article, c'est le même. Change de sujet, ou")
    print("  écris en une phrase ce que le tien ajoute — et cette phrase va dans le résumé")
    print("  de choix, pas dans la réponse finale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
