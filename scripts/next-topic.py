#!/usr/bin/env python3
"""Topic source for the S3 article series (three per week).

  python3 scripts/next-topic.py          -> prints the next unwritten topic as JSON
  python3 scripts/next-topic.py --list   -> every unwritten topic + the tags they add to
  python3 scripts/next-topic.py --status -> progress per segment
  exit 3 when every topic has been written

The queue is content/topics.json. Its order is a suggestion, not an
obligation: the series is published three times a week and the topic is chosen
each time from what the readers actually read, what search engines ask for but
the sites do not answer, and which tag is one article short of becoming an
indexable page. This script exists to show the remaining choices with enough
context to make that call — see content/AUTHORING.md, "Choosing the topic".
"""
import json, os, sys, glob
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "content", "topics.json")

queue = json.load(open(QUEUE, encoding="utf-8"))
topics = queue["topics"]
written = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "content", "blog", "*.md"))}
done = [t for t in topics if t["slug"] in written]
pending = [t for t in topics if t["slug"] not in written]

if "--status" in sys.argv:
    by = Counter(t["segment"] for t in topics)
    by_done = Counter(t["segment"] for t in done)
    print(f"{len(done)}/{len(topics)} written\n")
    print(f"{'SEGMENT':<14}{'DONE':>6}{'TOTAL':>7}")
    for seg in by:
        print(f"{seg:<14}{by_done.get(seg,0):>6}{by[seg]:>7}")
    print(f"\nnext: {pending[0]['slug'] if pending else '—'}")
    sys.exit(0 if pending else 3)

if "--list" in sys.argv:
    # Combien d'articles portent déjà chaque tag : c'est ce qui décide si un
    # sujet fait franchir le seuil d'indexation d'une page de tag.
    tag_counts = Counter()
    for t in done:
        for tag in t.get("tags", []):
            tag_counts[tag] += 1
    out = []
    for t in pending:
        entry = dict(t)
        entry["tags_now"] = {tag: tag_counts.get(tag, 0) for tag in t.get("tags", [])}
        entry["tags_at_publish"] = {tag: tag_counts.get(tag, 0) + 1 for tag in t.get("tags", [])}
        out.append(entry)
    print(json.dumps({"written": len(done), "remaining": len(pending), "topics": out},
                     ensure_ascii=False, indent=2))
    sys.exit(0)

if not pending:
    print("all topics written", file=sys.stderr)
    sys.exit(3)

t = dict(pending[0])
t["position"] = f"{len(done)+1}/{len(topics)}"
t["remaining"] = len(pending)
print(json.dumps(t, ensure_ascii=False, indent=2))
