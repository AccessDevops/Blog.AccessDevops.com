#!/usr/bin/env python3
"""Generate public/diagrams/etag-is-not-md5-on-multipart.svg.

    python3 scripts/etag-diagram.py

One 20 MiB payload, three upload paths, three different ETags — the values are
the ones scripts/etag-probe.py returned on 18 November 2026 against SeaweedFS
4.50. The bottom band carries the composite rule and the copy deviation.

Labels are sized for the ~5.7 px/character of 11.5 px Inter and the ~6.3 px/
character of 10.5 px mono; scripts/diagram-fit.py checks the render.
"""
import pathlib

INK, ACCENT, MUTED, RULE, CARD = "#020817", "#2563EB", "#64748B", "#E2E8F0", "#FFFFFF"
SANS = "Inter, system-ui, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

FILE_MD5 = "4ffc00e6e0d625f936b806a86a392c98"
SINGLE = "4ffc00e6e0d625f936b806a86a392c98"
TWO = "fbad3182280f8de3b9cb78094f2fb990-2"
FOUR = "c87fa7c13b8a90030bbaa9fe45870eb2-4"

COLS = [24, 330, 636]
CW = 280
PAD = 16

parts = [
    ("One PUT", [(1, "part 1 — 20 MiB")], SINGLE, "= MD5 of the file"),
    ("Multipart, 2 parts", [(1, "1 — 10 MiB"), (2, "2 — 10 MiB")], TWO, "≠ MD5 of the file"),
    ("Multipart, 4 parts", [(i, f"{i} — 5 MiB") for i in range(1, 5)], FOUR, "≠ MD5 of the file"),
]

TILE_TOP, TILE_BOTTOM = 104, 258  # all three columns occupy the same vertical band


def tile_heights(n: int) -> list[int]:
    gap = 6
    h = (TILE_BOTTOM - TILE_TOP - gap * (n - 1)) // n
    return [h] * n


def svg() -> str:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="940" height="596" viewBox="0 0 940 596" role="img" aria-labelledby="t d">',
        '  <title id="t">The same 20 MiB file uploaded three ways produces three different ETags</title>',
        '  <desc id="d">One PUT returns the MD5 of the file. A two-part and a four-part multipart upload of identical bytes return a hash of the part hashes with a dash and the part count appended, so neither equals the file MD5. A bottom band gives the composite rule and the measured case where a server-side copy kept the composite ETag instead of reverting to an MD5.</desc>',
        "",
        f'  <rect x="0" y="0" width="940" height="596" fill="{CARD}"/>',
        f'  <text x="24" y="40" font-family="{SANS}" font-size="13" font-weight="600" fill="{INK}">Same file, 20 MiB, MD5 {FILE_MD5[:8]}…{FILE_MD5[-8:]}</text>',
        f'  <text x="24" y="62" font-family="{SANS}" font-size="11.5" fill="{MUTED}">Three upload paths, three ETags. The object never changed.</text>',
    ]

    for (name, tiles, etag, verdict), x in zip(parts, COLS):
        centre = x + CW // 2
        out.append("")
        out.append(f'  <text x="{centre}" y="{TILE_TOP - 14}" text-anchor="middle" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{INK}">{name}</text>')

        hs = tile_heights(len(tiles))
        y = TILE_TOP
        for (_, label), h in zip(tiles, hs):
            out.append(f'  <rect x="{x}" y="{y}" width="{CW}" height="{h}" fill="{CARD}" stroke="{RULE}" stroke-width="1"/>')
            tx, ty, anchor = x + PAD, y + h // 2 + 4, "start"
            if len(tiles) * h < 100:
                tx, anchor = centre, "middle"
            out.append(f'  <text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="{SANS}" font-size="11.5" fill="{MUTED}">{label}</text>')
            y += h + 6

        # arrow from the upload column into its ETag box
        out.append(f'  <line x1="{centre}" y1="{TILE_BOTTOM + 4}" x2="{centre}" y2="{TILE_BOTTOM + 22}" stroke="{ACCENT}" stroke-width="1"/>')
        out.append(f'  <path d="M{centre - 4} {TILE_BOTTOM + 20} L{centre} {TILE_BOTTOM + 28} L{centre + 4} {TILE_BOTTOM + 20} Z" fill="{ACCENT}"/>')

        # ETag box
        by = TILE_BOTTOM + 32
        out.append(f'  <rect x="{x}" y="{by}" width="{CW}" height="60" fill="{CARD}" stroke="{RULE}" stroke-width="1"/>')
        out.append(f'  <text x="{x + PAD}" y="{by + 20}" font-family="{SANS}" font-size="10.5" fill="{MUTED}" letter-spacing="0.06em">ETAG</text>')
        out.append(f'  <text x="{x + PAD}" y="{by + 44}" font-family="{MONO}" font-size="10.5" fill="{INK}">{etag}</text>')

        # verdict
        colour = ACCENT if verdict.startswith("=") else INK
        out.append(f'  <text x="{centre}" y="{by + 86}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{colour}">{verdict}</text>')

    # bottom band: the rule
    out += [
        "",
        f'  <line x1="24" y1="404" x2="916" y2="404" stroke="{RULE}" stroke-width="1"/>',
        f'  <text x="24" y="432" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{INK}">The ETag identifies the upload, not the bytes</text>',
        f'  <text x="24" y="456" font-family="{SANS}" font-size="11.5" fill="{MUTED}">Single part, plaintext or SSE-S3:</text>',
        f'  <text x="210" y="456" font-family="{MONO}" font-size="11" fill="{INK}">ETag = MD5(bytes)</text>',
        f'  <text x="24" y="478" font-family="{SANS}" font-size="11.5" fill="{MUTED}">Any multipart upload:</text>',
        f'  <text x="210" y="478" font-family="{MONO}" font-size="11" fill="{ACCENT}">ETag = MD5(MD5(p1)..MD5(pn)) + "-n"</text>',
        "",
        f'  <rect x="24" y="500" width="892" height="76" fill="{CARD}" stroke="{RULE}" stroke-width="1"/>',
        f'  <text x="40" y="522" font-family="{SANS}" font-size="12" font-weight="600" fill="{INK}">Measured 18 November 2026, SeaweedFS 4.50</text>',
        f'  <text x="40" y="544" font-family="{SANS}" font-size="11.5" fill="{MUTED}">A server-side copy of the 4-part object came back as {FOUR[:8]}…-4, not as an MD5 — AWS documents a copy</text>',
        f'  <text x="40" y="562" font-family="{SANS}" font-size="11.5" fill="{MUTED}">of a plaintext object as an MD5. Two implementations of one API, two answers to the same question.</text>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    p = pathlib.Path(__file__).resolve().parent.parent / "public" / "diagrams" / "etag-is-not-md5-on-multipart.svg"
    p.write_text(svg(), encoding="utf-8")
    print(f"{p} — {p.stat().st_size} bytes")
