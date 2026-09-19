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
