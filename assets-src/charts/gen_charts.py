#!/usr/bin/env python3
"""Cost model + SVG charts for the S3 total-cost comparison article.
All list prices in USD, captured 2026-10-30 from vendor pricing pages (see PRICES notes)."""
import os, math

OUT = "public/charts"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- price data
# storage: USD per GB-month ; egress: USD per GB (0 = free) ; free_egress_gb
# put/get: USD per 1M requests
P = {
    "AWS S3":    dict(storage=0.023,  egress=0.09, free_egress=100,  put=5.00,  get=0.40, base=0,   note="us-east-1, Standard"),
    "Google GCS":dict(storage=0.020,  egress=0.12, free_egress=100,  put=5.00,  get=0.40, base=0,   note="us-central1, Standard"),
    "Cloudflare R2": dict(storage=0.015, egress=0.0, free_egress=0,  put=4.50,  get=0.36, base=0,   note="Standard, egress free"),
    "Backblaze B2": dict(storage=0.00695, egress=0.01, free_egress=0, put=0,    get=0,    base=0,   note="egress free up to 3x stored"),
    "Wasabi":    dict(storage=0.00799, egress=0.0, free_egress=0,    put=0,     get=0,    base=0,   note="flat, 90-day minimum, 1 TB min"),
    "DO Spaces": dict(storage=0.02,   egress=0.01, free_egress=1024, put=0,     get=0,    base=5,   note="$5 incl. 250 GiB + 1 TiB"),
    "OVHcloud":  dict(storage=0.0157, egress=0.0, free_egress=0,     put=0,     get=0,    base=0,   note="Standard 3-AZ, no egress/API fees"),
    "MinIO (self-hosted)": dict(storage=0.003, egress=0.0, free_egress=0, put=0, get=0,  base=0,   note="amortised infra, ~0.002-0.004"),
}
B2_FREE_RATIO = 3.0      # Backblaze: egress free up to 3x average stored
DO_INCLUDED_GB = 250     # DO Spaces base includes 250 GiB

def cost(name, store_gb, egress_gb, put_m, get_m):
    p = P[name]
    if name == "MinIO (self-hosted)":
        # fixed-cost assumption: one node = ~30 TB usable, $55/mo all-in (hardware amortised + power + colo/host)
        return math.ceil(store_gb / (30 * TB)) * 55
    c = p["base"]
    # storage
    if name == "DO Spaces":
        c += max(0, store_gb - DO_INCLUDED_GB) * p["storage"]
    else:
        c += store_gb * p["storage"]
    # egress
    if name == "Backblaze B2":
        c += max(0, egress_gb - B2_FREE_RATIO * store_gb) * p["egress"]
    else:
        c += max(0, egress_gb - p["free_egress"]) * p["egress"]
    # requests
    c += put_m * p["put"] + get_m * p["get"]
    return c

TB = 1024.0  # GB per TB (binary, as S3 bills)

SCENARIOS = {
    "Backup & archive": dict(store=10*TB, egress=0.5*TB, put=1, get=2,
        desc="10 TB stored, 5% served per month"),
    "Application data": dict(store=10*TB, egress=3*TB, put=20, get=200,
        desc="10 TB stored, 30% served, heavy API use"),
    "Media distribution": dict(store=5*TB, egress=20*TB, put=2, get=300,
        desc="5 TB stored, 400% served per month"),
    "Cross-region DR":  dict(store=20*TB, egress=1*TB, put=1, get=5,
        desc="10 TB + 10 TB replica, 5% served"),
}

# ---------------------------------------------------------------- compute
print("Provider | " + " | ".join(SCENARIOS))
results = {}
for s, cfg in SCENARIOS.items():
    results[s] = {n: cost(n, cfg["store"], cfg["egress"], cfg["put"], cfg["get"]) for n in P}
    print(f"{s}: " + ", ".join(f"{n.split(' ')[0]}={v:,.0f}" for n, v in sorted(results[s].items(), key=lambda x: x[1])))

# ---------------------------------------------------------------- svg helpers
TEAL, TEAL2, INK, MUTED, GRID = "#0f766e", "#26d0b5", "#111827", "#6b7280", "#e5e7eb"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def bar_chart(title, subtitle, data, width=760):
    """Horizontal bars, sorted desc, one chart per scenario."""
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    mx = max(v for _, v in items) or 1
    rowh, pad_top, left = 34, 74, 250
    height = pad_top + rowh * len(items) + 46
    bar_max = width - left - 100
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="{esc(title)}">']
    out.append(f'<text x="0" y="26" font-family="Inter,system-ui,sans-serif" font-size="19" font-weight="600" fill="{INK}">{esc(title)}</text>')
    out.append(f'<text x="0" y="50" font-family="Inter,system-ui,sans-serif" font-size="13" fill="{MUTED}">{esc(subtitle)}</text>')
    for i, (name, val) in enumerate(items):
        y = pad_top + i * rowh
        w = max(2, bar_max * val / mx)
        cheapest = i == len(items) - 1
        fill = TEAL2 if cheapest else TEAL
        out.append(f'<text x="0" y="{y+15}" font-family="Inter,system-ui,sans-serif" font-size="13.5" fill="{INK}">{esc(name)}</text>')
        out.append(f'<rect x="{left}" y="{y+3}" width="{w:.1f}" height="18" rx="4" fill="{fill}" opacity="{1 if cheapest else 0.85}"/>')
        out.append(f'<text x="{left+w+8:.1f}" y="{y+17}" font-family="ui-monospace,JetBrains Mono,monospace" font-size="12.5" fill="{INK}">${val:,.0f}</text>')
    out.append(f'<text x="0" y="{height-10}" font-family="Inter,system-ui,sans-serif" font-size="11.5" fill="{MUTED}">Monthly cost, USD. List prices, 2026-10-30. Lower is better.</text>')
    out.append("</svg>")
    return "\n".join(out)

def line_chart(width=760, height=420):
    """Cost vs monthly egress at 10 TB stored."""
    store = 10 * TB
    providers = ["AWS S3", "Google GCS", "Backblaze B2", "Cloudflare R2", "Wasabi", "DO Spaces", "OVHcloud", "MinIO (self-hosted)"]
    xs = [i * TB for i in range(0, 21)]  # 0..20 TB
    series = {}
    for n in providers:
        series[n] = [(x / TB, cost(n, store, x, 5, 50)) for x in xs]
    all_y = [v for s in series.values() for _, v in s]
    mx = max(all_y); mxy = math.ceil(mx / 500) * 500 or 500
    L, R, T, B = 62, 150, 34, 62
    pw, ph = width - L - R, height - T - B
    def X(tb): return L + pw * tb / 20
    def Y(v): return T + ph * (1 - v / mxy)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Monthly cost versus egress volume at 10 TB stored">']
    out.append(f'<text x="0" y="18" font-family="Inter,system-ui,sans-serif" font-size="17" font-weight="600" fill="{INK}">The egress cliff — 10 TB stored, egress from 0 to 20 TB/month</text>')
    for i in range(0, 6):
        v = mxy * i / 5
        y = Y(v)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="11" fill="{MUTED}">${v:,.0f}</text>')
    for t in range(0, 21, 5):
        out.append(f'<text x="{X(t):.1f}" y="{T+ph+22}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="11" fill="{MUTED}">{t} TB</text>')
    colors = {"AWS S3": "#b91c1c", "Google GCS": "#c2410c", "Backblaze B2": "#1d4ed8",
              "Cloudflare R2": TEAL2, "Wasabi": "#7c3aed", "DO Spaces": "#0891b2",
              "OVHcloud": "#15803d", "MinIO (self-hosted)": "#6b7280"}
    for n in providers:
        pts = " ".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in series[n])
        dash = ' stroke-dasharray="6 4"' if n == "MinIO (self-hosted)" else ""
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colors[n]}" stroke-width="2.4"{dash}/>')
    # legend, sorted by final value
    leg = sorted(providers, key=lambda n: series[n][-1][1], reverse=True)
    for i, n in enumerate(leg):
        y = T + 8 + i * 26
        out.append(f'<line x1="{L+pw+18}" y1="{y}" x2="{L+pw+40}" y2="{y}" stroke="{colors[n]}" stroke-width="3"/>')
        out.append(f'<text x="{L+pw+46}" y="{y+4}" font-family="Inter,system-ui,sans-serif" font-size="12" fill="{INK}">{esc(n.split(" (self")[0])}</text>')
        out.append(f'<text x="{L+pw+46}" y="{y+17}" font-family="ui-monospace,monospace" font-size="10.5" fill="{MUTED}">${series[n][-1][1]:,.0f}</text>')
    out.append("</svg>")
    return "\n".join(out)

# ---------------------------------------------------------------- write
for name, cfg in SCENARIOS.items():
    slug = name.lower().replace(" ", "-").replace("&", "and").replace("--", "-")
    svg = bar_chart(name, cfg["desc"], results[name])
    open(f"{OUT}/cost-{slug}.svg", "w").write(svg)
open(f"{OUT}/egress-cliff.svg", "w").write(line_chart())
print("\nwrote", len(SCENARIOS) + 1, "charts to", OUT)

# ---------------------------------------------------------------- csv snapshot
with open("assets-src/charts/model-output.csv", "w") as f:
    f.write("provider," + ",".join(s.replace(",", "") for s in SCENARIOS) + "\n")
    for n in P:
        f.write(n + "," + ",".join(f"{results[s][n]:.2f}" for s in SCENARIOS) + "\n")
print("wrote model-output.csv")
