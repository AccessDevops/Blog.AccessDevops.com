#!/usr/bin/env python3
"""Emit public/diagrams/block-public-access-four-switches.svg.

Flat fills, one accent, 1px rules. No external fonts, no gradients.
Body text is 11.5 px, so keep every line under ~80 characters (5.7 px/char).
"""
from pathlib import Path

W, H = 940, 684
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

out = []
a = out.append

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="bt bd">')
a('<title id="bt">Block Public Access is four independent switches that act at different moments, and the most restrictive level wins</title>')
a('<desc id="bd">Four switches on the left. BlockPublicAcls refuses a public ACL at write time. IgnorePublicAcls accepts the write and ignores the grant when a request is evaluated, while the ACL stays stored. BlockPublicPolicy refuses a PutBucketPolicy whose document allows public access. RestrictPublicBuckets removes all cross-account access from a bucket whose policy is public, including access granted to a named account. On the right, an unsigned GET is evaluated against organisation, account, bucket and access point settings, and S3 applies the most restrictive combination. At the bottom, the stored public grant survives every switch: turning a switch off restores the public response.</desc>')

a(f'<rect width="{W}" height="{H}" fill="{C["card"]}"/>')
a(f'<text x="34" y="46" font-family="{SANS}" font-size="18" font-weight="600" letter-spacing="-0.02em" fill="{C["ink"]}">Four switches, four different jobs</text>')
a(f'<text x="34" y="70" font-family="{SANS}" font-size="12.5" fill="{C["muted"]}">Each one blocks at a different moment. Removing one restores whatever it was hiding.</text>')

# ---------------- left panel: the four settings ----------------
a(f'<rect x="34" y="92" width="556" height="440" rx="10" fill="{C["card"]}" stroke="{C["rule"]}"/>')
a(f'<text x="54" y="118" font-family="{SANS}" font-size="10" letter-spacing="0.08em" fill="{C["muted"]}">THE BUCKET-LEVEL SETTINGS, AND WHAT EACH ONE STOPS</text>')

rows = [
    (
        "BlockPublicAcls",
        "write time",
        [
            "PutObjectAcl and PutObject carrying a public ACL fail.",
            "ACLs already stored keep working: not retroactive.",
        ],
        "403 on the write",
    ),
    (
        "IgnorePublicAcls",
        "evaluation",
        [
            "The public ACL is accepted, then ignored when a request",
            "is evaluated. It stays stored and reads as public.",
        ],
        "200 stored, 403 served",
    ),
    (
        "BlockPublicPolicy",
        "write time",
        [
            "PutBucketPolicy is rejected when the document allows",
            "public access. Existing policies are untouched, and a",
            "policy can grant the right to switch this one off.",
        ],
        "holds at account level only",
    ),
    (
        "RestrictPublicBuckets",
        "evaluation",
        [
            "Once any statement makes the policy public, every",
            "cross-account use goes, named accounts included.",
        ],
        "collateral damage",
    ),
]

y = 132
for name, moment, lines, kind in rows:
    h = 84 + (len(lines) - 2) * 16
    a(f'<rect x="50" y="{y}" width="524" height="{h}" rx="8" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
    a(f'<text x="66" y="{y + 22}" font-family="{MONO}" font-size="12.5" font-weight="600" fill="{C["accent"]}">{name}</text>')
    chip_w = 12 + len(moment) * 5.9
    a(f'<rect x="{566 - chip_w}" y="{y + 9}" width="{chip_w}" height="18" rx="4" fill="{C["card"]}" stroke="{C["rule"]}"/>')
    a(f'<text x="{566 - chip_w / 2}" y="{y + 22}" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{C["muted"]}">{moment}</text>')
    ty = y + 42
    for line in lines:
        a(f'<text x="66" y="{ty}" font-family="{SANS}" font-size="11.5" fill="{C["ink"]}">{line}</text>')
        ty += 16
    a(f'<text x="66" y="{y + h - 12}" font-family="{MONO}" font-size="10.5" fill="{C["muted"]}">{kind}</text>')
    y += h + 12

# ---------------- right panel: evaluation ----------------
rx, ry, rw, rh = 606, 92, 300, 440
a(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="10" fill="{C["card"]}" stroke="{C["rule"]}"/>')
a(f'<text x="{rx + 20}" y="{ry + 24}" font-family="{SANS}" font-size="10" letter-spacing="0.08em" fill="{C["muted"]}">WHAT AN UNSIGNED GET IS CHECKED AGAINST</text>')

levels = [
    ("Organisation", "all four, on or off together"),
    ("Account", "every bucket, every region, eventually"),
    ("Bucket", "strict only if the account agrees"),
    ("Access point", "passthrough to its bucket ACLs"),
]
ly = ry + 38
for n, (name, note) in enumerate(levels):
    a(f'<rect x="{rx + 20}" y="{ly}" width="{rw - 40}" height="52" rx="7" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
    a(f'<text x="{rx + 34}" y="{ly + 21}" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{C["ink"]}">{name}</text>')
    a(f'<text x="{rx + 34}" y="{ly + 38}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">{note}</text>')
    ly += 58

a(f'<text x="{rx + 20}" y="{ly + 10}" font-family="{SANS}" font-size="11" fill="{C["ink"]}">The most restrictive of the four wins.</text>')
a(f'<rect x="{rx + 20}" y="{ly + 20}" width="{rw - 40}" height="50" rx="7" fill="{C["card"]}" stroke="{C["accent"]}"/>')
a(f'<text x="{rx + 34}" y="{ly + 40}" font-family="{MONO}" font-size="11.5" fill="{C["accent"]}">403 AccessDenied</text>')
a(f'<text x="{rx + 34}" y="{ly + 57}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">or 200 with the bytes, if nothing holds</text>')

# ---------------- bottom band ----------------
by = 552
a(f'<rect x="34" y="{by}" width="872" height="102" rx="10" fill="{C["soft"]}" stroke="{C["rule"]}"/>')
a(f'<text x="54" y="{by + 24}" font-family="{SANS}" font-size="10" letter-spacing="0.08em" fill="{C["muted"]}">THE SWITCHES NEVER DELETE THE GRANT</text>')
a(f'<text x="54" y="{by + 52}" font-family="{MONO}" font-size="11.5" fill="{C["ink"]}">object ACL public-read</text>')
a(f'<text x="54" y="{by + 72}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">still stored, still public on paper</text>')

a(f'<line x1="262" y1="{by + 60}" x2="322" y2="{by + 60}" stroke="{C["accent"]}" stroke-width="1"/>')
a(f'<path d="M 322 {by + 55} L 332 {by + 60} L 322 {by + 65} z" fill="{C["accent"]}"/>')
a(f'<text x="262" y="{by + 48}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">switch on</text>')

a(f'<rect x="336" y="{by + 34}" width="200" height="52" rx="7" fill="{C["card"]}" stroke="{C["rule"]}"/>')
a(f'<text x="352" y="{by + 56}" font-family="{MONO}" font-size="11.5" fill="{C["ink"]}">GET \u2192 403</text>')
a(f'<text x="352" y="{by + 74}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">the bytes do not leave</text>')

a(f'<line x1="544" y1="{by + 60}" x2="604" y2="{by + 60}" stroke="{C["muted"]}" stroke-width="1"/>')
a(f'<path d="M 604 {by + 55} L 614 {by + 60} L 604 {by + 65} z" fill="{C["muted"]}"/>')
a(f'<text x="544" y="{by + 48}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">switch off</text>')

a(f'<rect x="618" y="{by + 34}" width="270" height="52" rx="7" fill="{C["card"]}" stroke="{C["accent"]}"/>')
a(f'<text x="634" y="{by + 56}" font-family="{MONO}" font-size="11.5" fill="{C["accent"]}">GET \u2192 200</text>')
a(f'<text x="634" y="{by + 74}" font-family="{SANS}" font-size="10.5" fill="{C["muted"]}">the 2019 exposure comes back</text>')
a('</svg>')

Path("public/diagrams/block-public-access-four-switches.svg").write_text("\n".join(out), encoding="utf-8")
print("written")
