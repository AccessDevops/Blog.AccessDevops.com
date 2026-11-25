#!/usr/bin/env python3
"""Emit public/diagrams/incomplete-multipart-storage-leak.svg.

Flat fills, one accent, 1px rules. No external fonts, no gradients.
Body text is 11.5 px, so keep every line under ~80 characters (5.7 px/char).
"""
from pathlib import Path

W, H = 940, 530
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
PRICE = 0.023           # S3 Standard, us-east-1, first 50 TB, price list 2026-11-21
PER_NIGHT = 34          # GB left by a 40 GB dump that dies at 85 %
NIGHTS = 30
MAX_GB = 1100

X0, X1 = 104, 860
Y0, Y1 = 116, 404
sx = (X1 - X0) / NIGHTS
sy = (Y1 - Y0) / MAX_GB


def x(day: float) -> float:
    return X0 + day * sx


def y(gb: float) -> float:
    return Y1 - gb * sy


out = []
a = out.append

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
a('<title id="t">Orphaned multipart parts accumulate with every failed upload until something aborts them</title>')
a('<desc id="d">Cumulative storage held by incomplete multipart uploads from one 40 GB nightly dump that dies at 85 percent, '
  'leaving 34 GB of parts each night. Without a lifecycle rule the line climbs 34 GB a night to 1,020 GB after 30 nights, '
  'billed at 0.023 dollars per gigabyte-month, about 23.46 dollars a month and still rising. With an '
  'AbortIncompleteMultipartUpload rule at one day, only the two most recent nights sit on the bill, 68 GB, about 1.56 dollars. '
  'No object exists in either case: ListObjectsV2 returns zero keys while the parts are stored.</desc>')

a(f'<rect width="{W}" height="{H}" fill="{C["card"]}"/>')
a(f'<text x="34" y="46" font-family="{SANS}" font-size="18" font-weight="600" letter-spacing="-0.02em" fill="{C["ink"]}">'
  'One failed job a night, an accidental archive in a month</text>')
a(f'<text x="34" y="70" font-family="{SANS}" font-size="12.5" fill="{C["muted"]}">'
  'Orphaned parts from a 40 GB dump that dies at 85%, priced at $0.023/GB-month'
  ' (S3 Standard, us-east-1, 2026-11-21)</text>')

# ---------------- axes and grid ----------------
a(f'<rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
for gb in (0, 250, 500, 750, 1000):
    yy = y(gb)
    a(f'<line x1="{X0}" y1="{yy:.1f}" x2="{X1}" y2="{yy:.1f}" stroke="{C["rule"]}" stroke-width="1"/>')
    a(f'<text x="{X0 - 12}" y="{yy + 4:.1f}" text-anchor="end" font-family="{MONO}" font-size="10.5" '
      f'fill="{C["muted"]}">{gb:,} GB</text>')
    a(f'<text x="{X1 + 12}" y="{yy + 4:.1f}" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}">'
      f'${gb * PRICE:,.2f}</text>')
for day in (0, 5, 10, 15, 20, 25, 30):
    a(f'<text x="{x(day):.1f}" y="{Y1 + 20}" text-anchor="middle" font-family="{MONO}" font-size="10.5" '
      f'fill="{C["muted"]}">day {day}</text>')

# ---------------- series: no lifecycle rule ----------------
pts = " ".join(f"{x(d):.1f},{y(d * PER_NIGHT):.1f}" for d in range(0, NIGHTS + 1, 2))
a(f'<polyline points="{pts}" fill="none" stroke="{C["accent"]}" stroke-width="2.5" stroke-linejoin="round"/>')
a(f'<circle cx="{x(NIGHTS):.1f}" cy="{y(NIGHTS * PER_NIGHT):.1f}" r="4" fill="{C["accent"]}"/>')
a(f'<text x="{x(NIGHTS) - 16:.1f}" y="{y(NIGHTS * PER_NIGHT) - 26:.1f}" text-anchor="end" font-family="{SANS}" '
  f'font-size="12" font-weight="600" fill="{C["ink"]}">1,020 GB — $23.46/month</text>')
a(f'<text x="{x(NIGHTS) - 16:.1f}" y="{y(NIGHTS * PER_NIGHT) - 10:.1f}" text-anchor="end" font-family="{SANS}" '
  f'font-size="11" fill="{C["muted"]}">no rule, still growing 34 GB a night</text>')

# ---------------- series: AbortIncompleteMultipartUpload days=1 ----------------
a(f'<line x1="{X0}" y1="{y(2 * PER_NIGHT):.1f}" x2="{X1}" y2="{y(2 * PER_NIGHT):.1f}" '
  f'stroke="{C["ink"]}" stroke-width="2" stroke-dasharray="6 4"/>')
a(f'<text x="{X1 - 10}" y="{y(2 * PER_NIGHT) - 28:.1f}" text-anchor="end" font-family="{SANS}" font-size="12" '
  f'font-weight="600" fill="{C["ink"]}">68 GB — $1.56/month</text>')
a(f'<text x="{X1 - 10}" y="{y(2 * PER_NIGHT) - 12:.1f}" text-anchor="end" font-family="{SANS}" font-size="11" '
  f'fill="{C["muted"]}">AbortIncompleteMultipartUpload, DaysAfterInitiation=1: two nights at most</text>')

# ---------------- the invisible object ----------------
a(f'<rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}" fill="none" stroke="{C["rule"]}"/>')
a(f'<text x="{X0 + 16}" y="{Y0 + 24}" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}">'
  'ListObjectsV2 on this bucket: 0 keys, every day of the month</text>')

# ---------------- legend ----------------
a(f'<line x1="34" y1="452" x2="58" y2="452" stroke="{C["accent"]}" stroke-width="2.5"/>')
a(f'<text x="66" y="456" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">parts kept because nothing completes or aborts the upload</text>')
a(f'<line x1="470" y1="452" x2="494" y2="452" stroke="{C["ink"]}" stroke-width="2" stroke-dasharray="6 4"/>')
a(f'<text x="502" y="456" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">the same uploads after the abort rule fires</text>')

a(f'<text x="34" y="492" font-family="{SANS}" font-size="11" fill="{C["muted"]}">'
  'Measured on SeaweedFS 4.50: three 5 MiB parts left 15,728,640 bytes while ListObjectsV2 reported zero keys, '
  'and a refused completion left 1,049,600 more.</text>')

a("</svg>")

path = Path(__file__).resolve().parents[1] / "public" / "diagrams" / "incomplete-multipart-storage-leak.svg"
path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{path} {path.stat().st_size} bytes")
