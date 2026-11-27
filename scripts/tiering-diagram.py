#!/usr/bin/env python3
"""Emit public/diagrams/intelligent-tiering-128kb-rule.svg.

Flat fills, one accent, 1px rules, no external fonts. Body text 11.5 px so keep
every line under ~5.7 px per character.

Numbers come from scripts/tiering-cost-model.py --objects 1000000 --size 8KB
against the AWS price list published 2026-11-25.
"""
from pathlib import Path

W, H = 940, 500
C = {
    "ink": "#020817",
    "accent": "#2563EB",
    "muted": "#64748B",
    "rule": "#E2E8F0",
    "card": "#FFFFFF",
    "soft": "#F8FAFC",
}
SANS = "Inter, system-ui, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

X0, X1 = 214, 852          # plot width
MAX = 12.0                 # dollars, first-month total
BAR_H = 22
ROW_Y = [122, 170, 218, 266]
ROWS = [
    ("S3 Standard", 0.17, 0.17),
    ("Intelligent-Tiering", 0.17, 0.17),
    ("Standard-IA", 1.53, 11.53),
    ("One Zone-IA", 1.22, 11.22),
]


def px(dollars: float) -> float:
    return (X1 - X0) * dollars / MAX


out: list[str] = []
a = out.append

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
a('<title id="t">The same million small objects, priced across four storage classes</title>')
a('<desc id="d">One million objects of 8,000 bytes, 7.45 GiB of real data, priced from the Amazon S3 offer file for us-east-1 '
  'published 25 November 2026. S3 Standard costs 0.17 dollars a month and Intelligent-Tiering the same, because objects '
  'under 128 KB are never tiered and carry no monitoring fee. Standard-IA bills the objects as 128 KB each, 122.07 GiB, '
  'so storage alone is 1.53 dollars, and one-off transition requests add 10.00 dollars for a first month of 11.53. '
  'One Zone-IA is 1.22 dollars of storage plus the same 10.00 of requests. Glacier Instant Retrieval is not drawn: '
  '0.49 dollars of storage and 20.00 dollars of requests.</desc>')

a(f'<rect width="{W}" height="{H}" fill="{C["card"]}"/>')
a(f'<text x="34" y="44" font-family="{SANS}" font-size="19" font-weight="600" letter-spacing="-0.02em" fill="{C["ink"]}">'
  'One million 8 KB objects, one month on the bill</text>')
a(f'<text x="34" y="68" font-family="{SANS}" font-size="12.5" fill="{C["muted"]}">'
  '7.45 GiB of real bytes, list prices, us-east-1, price list published 2026-11-25</text>')

# gridlines
for dollars in (0, 3, 6, 9, 12):
    x = X0 + px(dollars)
    a(f'<line x1="{x:.1f}" y1="98" x2="{x:.1f}" y2="292" stroke="{C["rule"]}"/>')
    a(f'<text x="{x:.1f}" y="310" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}" text-anchor="middle">'
      f'{"0" if dollars == 0 else f"${dollars}"}</text>')

for (label, storage, total), y in zip(ROWS, ROW_Y):
    a(f'<text x="196" y="{y + 15}" font-family="{SANS}" font-size="12" fill="{C["ink"]}" text-anchor="end">{label}</text>')
    a(f'<rect x="{X0}" y="{y}" width="{px(total):.1f}" height="{BAR_H}" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
    a(f'<rect x="{X0}" y="{y}" width="{px(storage):.1f}" height="{BAR_H}" fill="{C["accent"]}"/>')
    transition = total - storage
    if transition > 0.5:
        a(f'<rect x="{X0 + px(storage):.1f}" y="{y}" width="{px(transition):.1f}" height="{BAR_H}" '
          f'fill="{C["ink"]}" opacity="0.82"/>')
        a(f'<text x="{X0 + px(total) - 8:.1f}" y="{y + 15}" font-family="{MONO}" font-size="11" '
          f'fill="{C["card"]}" text-anchor="end">${total:,.2f}</text>')
        a(f'<text x="{X0 + px(storage) - 8:.1f}" y="{y + 15}" font-family="{MONO}" font-size="10.5" '
          f'fill="{C["card"]}" text-anchor="end">${storage:,.2f}</text>')
    else:
        a(f'<text x="{X0 + px(total) + 8:.1f}" y="{y + 15}" font-family="{MONO}" font-size="11" '
          f'fill="{C["muted"]}">${total:,.2f}</text>')

# legend
ly = 330
a(f'<rect x="34" y="{ly - 9}" width="11" height="11" fill="{C["accent"]}"/>')
a(f'<text x="51" y="{ly}" font-family="{SANS}" font-size="11.5" fill="{C["muted"]}">storage for the month</text>')
a(f'<rect x="205" y="{ly - 9}" width="11" height="11" fill="{C["ink"]}" opacity="0.82"/>')
a(f'<text x="222" y="{ly}" font-family="{SANS}" font-size="11.5" fill="{C["muted"]}">'
  'one-off transition requests, 1,000,000 at $0.01 per 1,000</text>')

# the 128 KB arithmetic
a(f'<line x1="34" y1="352" x2="{W - 34}" y2="352" stroke="{C["rule"]}"/>')
a(f'<text x="34" y="378" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">'
  'Standard-IA bills 122.07 GiB for 7.45 GiB of data: the minimum-size charge alone is $1.43 a month.</text>')
a(f'<text x="34" y="398" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">'
  'Glacier Instant Retrieval, same objects: $0.49 of storage and $20.00 of transition requests.</text>')
a(f'<text x="34" y="418" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">'
  'Intelligent-Tiering is the same price as Standard here: below 128 KB there is no tier to move to.</text>')

# three behaviours band
by = 438
a(f'<rect x="34" y="{by}" width="{W - 68}" height="42" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
for i, txt in enumerate((
    'lifecycle: skipped by default',
    'Standard-IA: billed as 128 KB',
    'Intelligent-Tiering: untiered, no fee',
)):
    cx = 52 + i * 290
    a(f'<rect x="{cx}" y="{by + 18}" width="3" height="12" fill="{C["accent"]}"/>')
    a(f'<text x="{cx + 11}" y="{by + 28}" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}">{txt}</text>')

a('</svg>')
path = Path(__file__).resolve().parent.parent / "public" / "diagrams" / "intelligent-tiering-128kb-rule.svg"
path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(path, path.stat().st_size, "bytes")
