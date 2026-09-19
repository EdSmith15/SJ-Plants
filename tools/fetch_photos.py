#!/usr/bin/env python3
"""Download identifying photos for every species in the deck into photos/.

Usage:  python3 tools/fetch_photos.py            # uses the deck built into index.html
        python3 tools/fetch_photos.py deck.txt   # or any file in the Deck editor format

For each "Genus species" line it takes up to PER_SPECIES photographs from the
species' English Wikipedia article (lead/taxobox photo first), downloads the
original file from Wikimedia Commons, resizes it to at most MAX_EDGE pixels on
the long side (needs Pillow: pip install pillow) and saves it as
photos/<genus>-<species>.jpg, -2.jpg, -3.jpg ... Source file, author and
licence go in photos/CREDITS.md. A deck line whose fourth field is
"wiki:Some title" uses that Wikipedia article instead.
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    from PIL import Image, ImageOps
except ImportError:  # falls back to the article's own thumbnail sizes
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "photos")
UA = {"User-Agent": "BinomialDrill/1.0 (flashcard app; https://github.com/EdSmith15/SJ-Plants)"}
SKIP = re.compile(r"map|status|icon|logo|distribution|range|commons|wiki|question|edit|symbol"
                  r"|illustration|drawing|herbarium|botanical|koehler|thom|plate|sketch", re.I)
PER_SPECIES = 4
MAX_EDGE = 1600      # long side of the saved photo, in pixels
MIN_SOURCE = 700     # skip originals narrower than this
JPEG_QUALITY = 84


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def deck_lines(path=None):
    if path:
        text = open(path, encoding="utf-8").read()
    else:
        html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        m = re.search(r"var SAMPLE = \[(.*?)\]\.join", html, re.S)
        text = "\n".join(lit.replace("\\'", "'")
                         for lit in re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(1)))
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s*(?:\||;|\t| - | – )\s*", line)
        tokens = ["×" if t in ("x", "X", "×") else t for t in parts[0].split()]
        if not tokens or (tokens[0] == "×" and len(tokens) < 2):
            continue
        if tokens[0] == "×":
            genus, rest = "× " + tokens[1].capitalize(), tokens[2:]
        else:
            genus, rest = tokens[0].capitalize(), tokens[1:]
        if not [t for t in rest if t != "×"]:
            continue
        fourth = parts[3].strip() if len(parts) > 3 else ""
        wiki = fourth[5:].strip() if fourth.lower().startswith("wiki:") else ""
        yield genus, " ".join(rest).lower(), wiki


def media_list(title):
    url = "https://en.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        return json.loads(get(url))
    except Exception:
        return None


def article_images(genus, species, wiki):
    """Return [(file_title, largest srcset url)] for the species, lead image first."""
    name = genus + " " + species
    titles = ([wiki] if wiki else []) + [name]
    if "×" in name:
        titles.append(re.sub(r"× ?", "", name))
    for t in titles:
        data = media_list(t)
        if not data:
            continue
        items = [i for i in data.get("items", [])
                 if i.get("type") == "image" and i.get("srcset")
                 and re.search(r"\.(jpe?g|png|webp)$", i.get("title", ""), re.I)
                 and not SKIP.search(i.get("title", ""))]
        if not items:
            continue
        items.sort(key=lambda i: not i.get("leadImage"))
        out = []
        for it in items:
            srcs = [("https:" + e["src"]) if e["src"].startswith("//") else e["src"] for e in it["srcset"]]
            out.append((it["title"], srcs[-1]))
        return out
    return []


def file_info(file_title):
    """Original URL, width, author and licence from the Commons API."""
    q = urllib.parse.urlencode({
        "action": "query", "titles": file_title, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "format": "json",
    })
    data = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
    licence = meta.get("LicenseShortName", {}).get("value", "")
    return info["url"], int(info.get("width", 0)), artist, licence


def fetch_resized(url, fallback_url):
    if Image is None:
        return get(fallback_url)
    raw = get(url)
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return buf.getvalue()


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for genus, species, wiki in deck_lines(sys.argv[1] if len(sys.argv) > 1 else None):
        slug = re.sub(r"[^a-z]+", "-", (genus + "-" + species).lower()).strip("-")
        name = genus + " " + species
        first = os.path.join(OUT, slug + ".jpg")
        if os.path.exists(first) and os.path.getsize(first) > 0:
            print("kept    ", name)
            continue
        images = article_images(genus, species, wiki)
        if not images:
            print("no image", name)
            continue
        saved = 0
        for file_title, fallback in images:
            if saved >= PER_SPECIES:
                break
            try:
                url, width, artist, licence = file_info(file_title)
                if width and width < MIN_SOURCE:
                    print("small   ", name, "-", file_title, width, "px")
                    continue
                data = fetch_resized(url, fallback)
            except Exception as e:
                print("failed  ", name, "-", file_title, "-", e)
                continue
            dest = os.path.join(OUT, slug + ("" if saved == 0 else "-%d" % (saved + 1)) + ".jpg")
            with open(dest, "wb") as f:
                f.write(data)
            page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(file_title)
            rows.append((name, os.path.basename(dest), file_title, artist, licence, page))
            print("saved   ", name, "<-", file_title, "(%d KB)" % (len(data) // 1024))
            saved += 1
    if rows:
        path = os.path.join(OUT, "CREDITS.md")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write("# Photo credits\n\nAll photos from Wikimedia Commons under the licence shown.\n\n")
            for name, fn, ft, artist, licence, page in rows:
                f.write(f"- **{name}** — `{fn}` — [{ft}]({page}) — {artist or 'unknown author'} — {licence or 'see file page'}\n")


if __name__ == "__main__":
    main()
