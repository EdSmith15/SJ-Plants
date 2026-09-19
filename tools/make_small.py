#!/usr/bin/env python3
"""Write reduced copies of every photo into photos/small/ (needs Pillow).
Used to build a self-contained version of the app with the photos embedded."""
import io, os, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "photos"); DST = os.path.join(SRC, "small")
MAX_EDGE, QUALITY = 720, 70
os.makedirs(DST, exist_ok=True)
total = 0
for name in sorted(os.listdir(SRC)):
    if not name.endswith(".jpg"):
        continue
    out = os.path.join(DST, name)
    src = os.path.join(SRC, name)
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        total += os.path.getsize(out); continue
    img = Image.open(src).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    img.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    total += os.path.getsize(out)
print("small set: %d files, %.1f MB" % (len(os.listdir(DST)), total / 1e6))
