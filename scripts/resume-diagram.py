#!/usr/bin/env python3
"""Generates public/diagrams/resume-interrupted-multipart-upload.svg.

    python3 scripts/resume-diagram.py

Palette and type rules follow content/AUTHORING.md: #020817 ink, #2563EB
accent, #64748B muted, #E2E8F0 rule, #FFFFFF card, flat fills, 1px strokes.
Label widths are checked by the caller with getBBox in headless Chrome.
"""
import os

W, H = 940, 680
INK, ACCENT, MUTED, RULE, CARD = "#020817", "#2563EB", "#64748B", "#E2E8F0", "#FFFFFF"
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "Inter, system-ui, sans-serif"

out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'role="img" aria-label="A multipart upload survives the process that started it: the upload id '
    'and the part ETags are still on the server after a crash, so the restart lists the upload, '
    'lists its parts and sends only the missing one — unless the part list returns a stale ETag for '
    'a re-sent part number">',
    f'<rect x="0" y="0" width="{W}" height="{H}" fill="{CARD}" stroke="none"/>',
]


def text(x, y, s, size=11.5, fill=MUTED, weight="400", font=MONO, anchor="start"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" '
               f'font-weight="{weight}" text-anchor="{anchor}">{s}</text>')


def box(x, y, w, h, fill=CARD, stroke=RULE, r=10):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
               f'stroke="{stroke}" stroke-width="1"/>')


def arrow(x1, y1, x2, y2, color=RULE):
    """Horizontal rule with a small solid head, so no marker defs are needed."""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2 - 7}" y2="{y2}" stroke="{color}" stroke-width="1"/>')
    out.append(f'<path d="M{x2 - 7} {y2 - 4} L{x2} {y2} L{x2 - 7} {y2 + 4} Z" fill="{color}"/>')


# ── stage 1: the upload outlives the process ────────────────────────────────
text(40, 40, "PUT /db.tar?uploads  →  POST ?partNumber=1,2  →  process exits", 12)
text(40, 60, "the upload id and the parts live on the server, not in your state file", 11.5)

box(40, 76, 250, 104)
text(58, 100, "CreateMultipartUpload", 12, INK, "600", SANS)
text(58, 122, "uploadId 1c1651d2…", 11)
text(58, 140, "no expiry server-side", 11.5, MUTED, "400", SANS)
text(58, 158, "complete or abort, or it stays", 11.5, MUTED, "400", SANS)

arrow(292, 128, 352, 128)

box(352, 76, 250, 104)
text(370, 100, "UploadPart 1 and 2", 12, INK, "600", SANS)
text(370, 122, "200 · ETag b325f8…", 11)
text(370, 140, "200 · ETag ac9271…", 11)
text(370, 158, "5 242 880 bytes each", 11.5, MUTED, "400", SANS)

arrow(604, 128, 664, 128)

box(664, 76, 236, 104, fill="#F1F5F9")
text(682, 100, "The uploader dies", 12, INK, "600", SANS)
text(682, 122, "ETags are in a temp file", 11.5, MUTED, "400", SANS)
text(682, 140, "the temp file is not", 11.5, MUTED, "400", SANS)
text(682, 158, "nothing is lost yet", 11.5, INK, "600", SANS)

out.append(f'<line x1="40" y1="204" x2="900" y2="204" stroke="{RULE}" stroke-width="1"/>')

# ── stage 2: the restart rebuilds the part list from the server ─────────────
text(40, 230, "After the restart — three calls, no state file", 12, INK, "600", SANS)

rows = [
    ("ListMultipartUploads", "1 in-progress upload for db.tar · IsTruncated false", 258),
    ("ListParts", "2 parts · each with its PartNumber, Size and ETag", 320),
    ("UploadPart 3", "the only missing part is re-sent · last part, 1 024 bytes", 382),
    ("CompleteMultipartUpload", "the parts list rebuilt from ListParts · 200 · 10 486 784 bytes", 444),
]
for name, detail, y in rows:
    box(40, y, 604, 48)
    text(60, y + 21, name, 12, INK, "600", SANS)
    text(60, y + 38, detail, 11.5, MUTED, "400", SANS)
    arrow(646, y + 24, 680, y + 24)

box(684, 258, 216, 234, fill="#F1F5F9")
text(702, 282, "Why it works", 12, INK, "600", SANS)
text(702, 306, "the server kept the", 11.5, MUTED, "400", SANS)
text(702, 322, "upload id alive, so", 11.5, MUTED, "400", SANS)
text(702, 338, "the resume needs the", 11.5, MUTED, "400", SANS)
text(702, 354, "endpoint, the bucket,", 11.5, MUTED, "400", SANS)
text(702, 370, "the key and the id —", 11.5, MUTED, "400", SANS)
text(702, 386, "not disk on the host", 11.5, MUTED, "400", SANS)
text(702, 414, "s3:ListMultipartUploadParts", 9.8, INK, "400", MONO)
text(702, 432, "s3:ListBucketMultipartUploads", 9.8, INK, "400", MONO)
text(702, 460, "the two permissions a", 11.5, MUTED, "400", SANS)
text(702, 476, "resume actually needs", 11.5, MUTED, "400", SANS)

# ── stage 3: the trap ───────────────────────────────────────────────────────
out.append(f'<line x1="40" y1="520" x2="900" y2="520" stroke="{RULE}" stroke-width="1"/>')
text(40, 546, "The part list is not always the truth — re-sending a part number", 12, INK, "600", SANS)

box(40, 558, 424, 60)
text(58, 580, "UploadPart 2 again → 200 with a new ETag", 11.5, INK, "600", SANS)
text(58, 600, "the part list should now show that new ETag", 11.5, MUTED, "400", SANS)

box(476, 558, 424, 60)
text(494, 580, "SeaweedFS 4.50: 4 of 10 trials", 11.5, INK, "600", SANS)
text(494, 600, "kept the previous ETag · old bytes stored", 11.5, ACCENT, "600", SANS)

text(40, 654, "Measured 13 November 2026: SeaweedFS 4.50 and moto 5.2.5, boto3 1.44.2 — scripts/resume-probe.py, scripts/resume-overwrite-probe.py", 10.5)

out.append("</svg>")

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "public", "diagrams", "resume-interrupted-multipart-upload.svg")
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(path, os.path.getsize(path), "bytes")
