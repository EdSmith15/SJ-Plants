#!/usr/bin/env python3
"""Copy photos/index.json into index.html's inline <script id="photoIndex"> block,
so the app needs no network request to know which photos exist."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(ROOT, "index.html")
index_path = os.path.join(ROOT, "photos", "index.json")
data = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else {}
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = open(html_path, encoding="utf-8").read()
new, n = re.subn(r'(<script type="application/json" id="photoIndex">).*?(</script>)',
                 lambda m: m.group(1) + payload + m.group(2), html, count=1, flags=re.S)
if n != 1:
    sys.exit("photoIndex block not found in index.html")
if new != html:
    open(html_path, "w", encoding="utf-8").write(new)
    print("embedded", len(data), "species into index.html")
else:
    print("index.html already up to date")
