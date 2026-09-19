#!/usr/bin/env python3
"""One-off probe: show how rhs.org.uk serves search results and plant photos."""
import re, sys, urllib.request, urllib.parse, gzip, io

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        return r.status, r.headers.get("Content-Type", ""), data.decode("utf-8", "replace")

def show(label, url):
    print("=" * 80); print(label, url)
    try:
        status, ctype, html = get(url)
    except Exception as e:
        print("ERROR", e); return ""
    print("status", status, ctype, "length", len(html))
    print("title:", re.findall(r"<title>(.*?)</title>", html, re.S)[:1])
    links = sorted(set(re.findall(r'href="(/plants/\d+/[^"]+)"', html)))
    print("plant links:", len(links)); print("\n".join(links[:15]))
    imgs = sorted(set(re.findall(r'(?:src|srcset|data-src|data-srcset)="([^"]*(?:getmedia|/media/|\.jpe?g|\.webp)[^"]*)"', html, re.I)))
    print("image urls:", len(imgs)); print("\n".join(imgs[:25]))
    apis = sorted(set(re.findall(r'"(https?://[^"]*rhs[^"]*(?:api|search)[^"]*)"', html, re.I)))
    print("api-ish urls:", len(apis)); print("\n".join(apis[:15]))
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    print("json-ld blocks:", len(ld)); [print(x[:600]) for x in ld[:2]]
    nxt = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    print("next-data:", len(nxt)); [print(x[:1200]) for x in nxt[:1]]
    return html

q = sys.argv[1] if len(sys.argv) > 1 else "Quercus robur"
html = show("SEARCH", "https://www.rhs.org.uk/plants/search-results?query=" + urllib.parse.quote(q))
m = re.search(r'href="(/plants/\d+/[^"]+)"', html or "")
if m:
    show("PLANT PAGE", "https://www.rhs.org.uk" + m.group(1))
else:
    show("PLANT PAGE (known)", "https://www.rhs.org.uk/plants/11839/ophiopogon-planiscapus/details")
show("SEARCH API guess", "https://www.rhs.org.uk/api/plantsearch?query=" + urllib.parse.quote(q))

# ---- second pass: image sizes and the RHS Digital Collections site ----
def head(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Content-Type"), r.headers.get("Content-Length")
    except Exception as e:
        return "ERR", str(e)[:80], None

def jpeg_size(data):
    i = 2
    while i < len(data):
        if data[i] != 0xFF: return None
        marker = data[i+1]; ln = int.from_bytes(data[i+2:i+4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i+7:i+9], "big"), int.from_bytes(data[i+5:i+7], "big")
        i += 2 + ln
    return None

print("=" * 80); print("IMAGE VARIANTS for elbo57432")
for variant in ["detail", "large", "full", "original", "zoom", "medium", "thumb", "listing"]:
    u = "https://apps.rhs.org.uk/plantselectorimages/%s/elbo57432.jpg" % variant
    print(variant, head(u))
try:
    req = urllib.request.Request("https://apps.rhs.org.uk/plantselectorimages/detail/elbo57432.jpg", headers=UA)
    data = urllib.request.urlopen(req, timeout=30).read()
    print("detail bytes", len(data), "dimensions", jpeg_size(data))
except Exception as e:
    print("detail fetch error", e)

print("=" * 80); print("PLANT PAGE image context")
try:
    _, _, h = get("https://www.rhs.org.uk/plants/11839/ophiopogon-planiscapus/details")
    for m in re.finditer(r'<img[^>]*plantselectorimages[^>]*>', h):
        print(m.group(0)[:400])
    for m in re.finditer(r'.{0,200}plantselectorimages/detail/elbo57432.{0,200}', h, re.S):
        print("CTX:", re.sub(r"\s+", " ", m.group(0))[:500]); break
    for m in re.finditer(r'<script[^>]+src="([^"]+)"', h):
        print("script:", m.group(1))
except Exception as e:
    print("err", e)

print("=" * 80); print("RHS DIGITAL COLLECTIONS")
for u in ["https://collections.rhs.org.uk/search?q=" + urllib.parse.quote(q),
          "https://collections.rhs.org.uk/results?q=" + urllib.parse.quote(q),
          "https://collections.rhs.org.uk/?q=" + urllib.parse.quote(q),
          "https://collections.rhs.org.uk/view/92898/ophiopogon-planiscapus-kokuryu"]:
    try:
        status, ctype, h = get(u)
        print(u, status, ctype, len(h))
        print("  title:", re.findall(r"<title>(.*?)</title>", h, re.S)[:1])
        views = sorted(set(re.findall(r'href="(/view/\d+/[^"?]+)', h)))
        print("  view links:", len(views), views[:8])
        imgs = sorted(set(re.findall(r'(?:src|srcset|data-src|href)="([^"]*(?:\.jpe?g|\.png|iiif|thumb|image)[^"]*)"', h, re.I)))
        print("  images:", len(imgs)); [print("   ", x[:200]) for x in imgs[:12]]
        apis = sorted(set(re.findall(r'["\'](https?://[^"\']*(?:api|iiif|search)[^"\']*)["\']', h, re.I)))
        print("  api-ish:", apis[:8])
        for m in re.finditer(r'<script[^>]+src="([^"]+)"', h):
            print("  script:", m.group(1)[:160])
    except Exception as e:
        print(u, "ERROR", e)
