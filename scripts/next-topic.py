#!/usr/bin/env python3
"""Queue driver for the daily S3 article series.

  python3 scripts/next-topic.py          -> prints the next unwritten topic as JSON
  python3 scripts/next-topic.py --status -> prints progress per segment
  exit 3 when every topic has been written

The queue is content/topics.json, order is authoritative, completion is
detected by the existence of content/blog/<slug>.md. Idempotent: re-running
after a successful write returns the following topic.
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

if not pending:
    print("all topics written", file=sys.stderr)
    sys.exit(3)

t = dict(pending[0])
t["position"] = f"{len(done)+1}/{len(topics)}"
t["remaining"] = len(pending)
print(json.dumps(t, ensure_ascii=False, indent=2))
