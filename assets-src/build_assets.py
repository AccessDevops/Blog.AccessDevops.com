#!/usr/bin/env python3
"""Generate OG image + app icons by rendering local HTML (HTTP) with embedded fonts via headless Chrome."""
import urllib.request, re, base64, os, subprocess
import http.server, socketserver, threading, functools
from PIL import Image

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
CSS_URL = ("https://fonts.googleapis.com/css2?"
           "family=Inter:wght@400;500;600&"
           "family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&"
           "family=JetBrains+Mono:wght@400;500&display=swap")
CHROME = "/home/hermes/.hermes/tools/chromium-1208/chrome-linux64/chrome"
PORT = 8931
CHROME_CHROME_H = 88  # old headless window height - viewport height

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode()

print("fetching font CSS...")
css = fetch(CSS_URL)
urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))
print(len(urls), "font files")
for u in urls:
    css = css.replace(u, "data:font/woff2;base64," + base64.b64encode(fetch(u, True)).decode())
print("embedded, css bytes:", len(css))

os.makedirs(".chrome-tmp", exist_ok=True)
_handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", PORT), _handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def render(tpl, out, w, h):
    html = open(tpl).read()
    html = re.sub(r"<link[^>]*fonts\.googleapis[^>]*>", "<style>" + css + "</style>", html)
    inline = tpl.replace(".html", "-inline.html")
    open(inline, "w").write(html)
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           f"--window-size={w},{h + CHROME_CHROME_H}",
           f"--screenshot={os.path.abspath(out)}",
           "--user-data-dir=" + os.path.abspath(".chrome-tmp"),
           f"http://127.0.0.1:{PORT}/" + os.path.relpath(inline)]
    print("rendering", out, f"{w}x{h}")
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        print("  rc=%s" % r.returncode)
    except subprocess.TimeoutExpired:
        print("  TIMEOUT"); return
    if os.path.exists(out):
        im = Image.open(out)
        if im.size != (w, h):
            im.crop((0, 0, w, h)).save(out)
            print("  cropped", im.size, "->", (w, h))
        print("  ok", Image.open(out).size, os.path.getsize(out), "bytes")

render("assets-src/og.html", "public/og-image.png", 1200, 630)
render("assets-src/icon.html", "public/icon-512.png", 512, 512)

if os.path.exists("public/icon-512.png"):
    icon = Image.open("public/icon-512.png").convert("RGBA")
    icon.resize((192, 192)).save("public/icon-192.png")
    icon.resize((180, 180)).save("public/apple-touch-icon.png")
    icon.resize((32, 32)).save("public/favicon-32.png")
    icon.resize((16, 16)).save("public/favicon-16.png")
    icon.save("public/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("resizes + ico OK")

for f in ["public/og-image.png", "public/icon-512.png"]:
    im = Image.open(f).convert("RGB"); w, h = im.size; bg = im.getpixel((1, 1)); last = 0
    for y in range(h):
        for x in range(0, w, 6):
            p = im.getpixel((x, y))
            if abs(p[0]-bg[0]) + abs(p[1]-bg[1]) + abs(p[2]-bg[2]) > 22:
                last = y; break
    print(f, im.size, "last_content_row", last, "bottom_margin", h - 1 - last)
