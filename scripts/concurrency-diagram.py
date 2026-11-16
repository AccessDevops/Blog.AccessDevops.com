#!/usr/bin/env python3
"""Build public/diagrams/parallel-parts-vs-single-stream.svg from the
measured medians printed by scripts/concurrency-probe.py.

    python3 scripts/concurrency-diagram.py

The numbers below are the medians of five runs each, 256 MiB file, against
SeaweedFS 4.50 on 127.0.0.1 (same 6 vCPU machine), boto3 1.34.46.
Keep this list and the article table identical: the chart is generated from
it so the two cannot drift.
"""
import pathlib

# (part_mib, concurrency, median MiB/s, min, max)
RUNS = [
    (8, 1, 26.6, 23.4, 34.3),
    (8, 2, 54.3, 44.2, 59.1),
    (8, 4, 65.2, 49.8, 90.2),
    (8, 8, 79.1, 69.0, 89.9),
    (8, 16, 59.3, 48.6, 99.1),
    (32, 1, 43.4, 38.1, 50.9),
    (32, 2, 65.7, 52.8, 73.8),
    (32, 4, 107.0, 57.8, 116.7),
    (32, 8, 99.6, 62.4, 103.8),
    (32, 16, 94.5, 82.1, 109.9),
]
SINGLE_PUT = (59.2, 47.9, 88.9)

W, H = 1010, 516
INK, ACCENT, MUTED, RULE, CARD = "#020817", "#2563EB", "#64748B", "#E2E8F0", "#FFFFFF"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "Inter, system-ui, -apple-system, sans-serif"

X0, X1 = 92, 902          # plot area
Y_TOP, Y_BASE = 84, 392   # 120 MiB/s at Y_TOP, 0 at Y_BASE
Y_MAX = 120.0
CONCURRENCIES = [1, 2, 4, 8, 16]
GROUP_STEP = (X1 - X0) / len(CONCURRENCIES)
BAR_W = 44


def y(v):
    return Y_BASE - (v / Y_MAX) * (Y_BASE - Y_TOP)


def main():
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Upload throughput against number of parts in flight">',
           f'<rect width="{W}" height="{H}" fill="{CARD}"/>',
           f'<text x="40" y="34" font-family="{SANS}" font-size="15.5" font-weight="600" '
           f'fill="{INK}">256 MiB to one endpoint: more parts in flight, then nothing</text>',
           f'<text x="40" y="55" font-family="{SANS}" font-size="11.5" fill="{MUTED}">'
           f'median of 5 runs, SeaweedFS 4.50 on loopback, 6 vCPU client, boto3 1.34.46</text>']

    # legend, top right, clear of the plot
    lx = 636
    for label, colour in (("8 MiB parts", MUTED), ("32 MiB parts", ACCENT)):
        out.append(f'<rect x="{lx}" y="58" width="10" height="10" fill="{colour}"/>')
        out.append(f'<text x="{lx + 15}" y="67" font-family="{SANS}" font-size="11" '
                   f'fill="{INK}">{label}</text>')
        lx += 112

    # y grid + labels
    for v in (0, 30, 60, 90, 120):
        yy = y(v)
        out.append(f'<line x1="{X0}" y1="{yy:.1f}" x2="{X1}" y2="{yy:.1f}" '
                   f'stroke="{RULE}" stroke-width="1"/>')
        out.append(f'<text x="{X0 - 12}" y="{yy + 4:.1f}" text-anchor="end" '
                   f'font-family="{MONO}" font-size="10.5" fill="{MUTED}">{v}</text>')
    out.append(f'<text x="{X0}" y="{Y_TOP - 12}" font-family="{SANS}" '
               f'font-size="10.5" fill="{MUTED}">MiB/s</text>')

    # single PUT reference line, labelled in the right margin
    sy = y(SINGLE_PUT[0])
    out.append(f'<line x1="{X0}" y1="{sy:.1f}" x2="{X1}" y2="{sy:.1f}" stroke="{INK}" '
               f'stroke-width="1" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{X1 + 12}" y="{sy - 1:.1f}" font-family="{MONO}" font-size="10" '
               f'fill="{INK}">single PUT</text>')
    out.append(f'<text x="{X1 + 12}" y="{sy + 12:.1f}" font-family="{MONO}" font-size="10" '
               f'fill="{INK}">no parts: 59.2</text>')

    for i, c in enumerate(CONCURRENCIES):
        cx = X0 + GROUP_STEP * (i + 0.5)
        for j, part in enumerate((8, 32)):
            _, _, med, lo, hi = [r for r in RUNS if r[0] == part and r[1] == c][0]
            bx = cx - BAR_W - 4 + j * (BAR_W + 8)
            colour = MUTED if part == 8 else ACCENT
            out.append(f'<rect x="{bx:.1f}" y="{y(med):.1f}" width="{BAR_W}" '
                       f'height="{y(0) - y(med):.1f}" fill="{colour}"/>')
            out.append(f'<line x1="{bx + BAR_W / 2:.1f}" y1="{y(lo):.1f}" '
                       f'x2="{bx + BAR_W / 2:.1f}" y2="{y(hi):.1f}" stroke="{INK}" '
                       f'stroke-width="1" opacity="0.55"/>')
            for edge in (lo, hi):
                out.append(f'<line x1="{bx + BAR_W / 2 - 5:.1f}" y1="{y(edge):.1f}" '
                           f'x2="{bx + BAR_W / 2 + 5:.1f}" y2="{y(edge):.1f}" '
                           f'stroke="{INK}" stroke-width="1" opacity="0.55"/>')
            out.append(f'<text x="{bx + BAR_W / 2:.1f}" y="{y(hi) - 7:.1f}" text-anchor="middle" '
                       f'font-family="{MONO}" font-size="10.5" fill="{INK}">{med:.0f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{Y_BASE + 20}" text-anchor="middle" '
                   f'font-family="{MONO}" font-size="11.5" fill="{INK}">{c}</text>')

    out.append(f'<text x="{(X0 + X1) / 2}" y="{Y_BASE + 42}" text-anchor="middle" '
               f'font-family="{SANS}" font-size="11.5" fill="{MUTED}">parts in flight '
               f'(max_concurrency)</text>')

    # captions, in their own band under the axis
    for i, line in enumerate((
        "One thread with parts is slower than no parts at all: 27 MiB/s against 59, because "
        "each of the 32 parts pays its own round trip.",
        "Past four parts in flight the client burns 0.9 -> 1.4 CPU cores and throughput stops rising.",
    )):
        out.append(f'<text x="{X0}" y="{Y_BASE + 70 + i * 18}" font-family="{SANS}" '
                   f'font-size="11" fill="{INK}">{line}</text>')

    out.append(f'<text x="{X0}" y="{H - 18}" font-family="{SANS}" font-size="10.5" '
               f'fill="{MUTED}">whiskers: min-max across the 5 runs. Reproduce: '
               f'python3 scripts/concurrency-probe.py run http://127.0.0.1:18333 bench --size-mib 256 --reps 5</text>')
    out.append('</svg>')

    p = pathlib.Path("public/diagrams/parallel-parts-vs-single-stream.svg")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out) + "\n")
    print(f"{p} {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
