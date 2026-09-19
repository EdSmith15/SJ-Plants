#!/usr/bin/env python3
"""Download identifying photos for every species in the deck into photos/.

Usage:  python3 tools/fetch_photos.py            # uses the deck built into index.html
        python3 tools/fetch_photos.py deck.txt   # or any file in the Deck editor format

Sources, in order:
  1. The species' page on rhs.org.uk (sixth deck field = RHS plant page
     number): every photo in the page's image gallery.
  2. If that gives fewer than MIN_TOTAL photos, the species' English Wikipedia
     article (Wikimedia Commons originals), up to PER_SPECIES in total.

Photos are resized to at most MAX_EDGE pixels on the long side (Pillow) and
saved as photos/<genus>-<species>.jpg, -2.jpg, -3.jpg ... Each photo's source
is recorded in photos/index.json (read by the app) and photos/CREDITS.md.
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "photos")
INDEX = os.path.join(OUT, "index.json")
BROWSER_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BOT_UA = "SJPlants/1.0 (flashcard app; https://github.com/EdSmith15/SJ-Plants)"
SKIP = re.compile(r"map|status|icon|logo|distribution|range|commons|wiki|question|edit|symbol"
                  r"|illustration|drawing|herbarium|botanical|koehler|thom|plate|sketch", re.I)
PER_SPECIES = 5
MIN_TOTAL = 3
MAX_EDGE = 1600
MIN_SOURCE = 700
JPEG_QUALITY = 84
MIN_INTERVAL = 1.0
_last = {}


def get(url, timeout=60):
    """GET with a polite per-host request rate and backoff on 429 / 5xx."""
    host = urllib.parse.urlparse(url).netloc
    ua = BOT_UA if "wikimedia" in host or "wikipedia" in host else BROWSER_UA
    for attempt in range(6):
        wait = MIN_INTERVAL - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            time.sleep(5 * 2 ** attempt)


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
        rhs = parts[5].strip() if len(parts) > 5 and parts[5].strip().isdigit() else ""
        yield genus, " ".join(rest).lower(), wiki, rhs


# ---------------------------------------------------------------- RHS
def rhs_photos(page_id, slug):
    """[(image url, page url)] for every gallery photo on the RHS plant page."""
    page = "https://www.rhs.org.uk/plants/%s/%s/details" % (page_id, slug)
    html = get(page).decode("utf-8", "replace")
    urls = []
    for u in re.findall(r'https://apps\.rhs\.org\.uk/plantselectorimages/detail/[^"\'\s>]+\.jpe?g', html, re.I):
        if u not in urls:
            urls.append(u)
    canonical = re.search(r'"url":"(https://www\.rhs\.org\.uk/plants/\d+/[^"]+/details)"', html)
    return [(u, canonical.group(1) if canonical else page) for u in urls]


# ---------------------------------------------------------------- Wikipedia
def media_list(title):
    url = "https://en.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        return json.loads(get(url))
    except Exception:
        return None


def wiki_photos(genus, species, wiki):
    """[(file_title, fallback url)] for the species' article, lead image first."""
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
    q = urllib.parse.urlencode({"action": "query", "titles": file_title, "prop": "imageinfo",
                                "iiprop": "url|size|extmetadata", "format": "json"})
    data = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
    licence = meta.get("LicenseShortName", {}).get("value", "")
    return info["url"], int(info.get("width", 0)), artist, licence


# ---------------------------------------------------------------- images
def resized(raw):
    if Image is None:
        return raw
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return buf.getvalue()


def main():
    os.makedirs(OUT, exist_ok=True)
    index = {}
    if os.path.exists(INDEX):
        try:
            index = json.load(open(INDEX, encoding="utf-8"))
        except Exception:
            index = {}
    credit_rows = []

    for genus, species, wiki, rhs in deck_lines(sys.argv[1] if len(sys.argv) > 1 else None):
        slug = re.sub(r"[^a-z]+", "-", (genus + "-" + species).lower()).strip("-")
        name = genus + " " + species
        first = os.path.join(OUT, slug + ".jpg")
        if os.path.exists(first) and os.path.getsize(first) > 0 and index.get(slug):
            print("kept    ", name)
            continue
        entries = []

        def save(data, source, page, title):
            n = len(entries)
            fn = slug + ("" if n == 0 else "-%d" % (n + 1)) + ".jpg"
            with open(os.path.join(OUT, fn), "wb") as f:
                f.write(data)
            entries.append({"file": fn, "source": source, "page": page, "title": title})
            print("saved   ", name, "<-", source, title, "(%d KB)" % (len(data) // 1024))

        # 1. RHS plant page gallery
        if rhs:
            try:
                for url, page in rhs_photos(rhs, slug)[:PER_SPECIES]:
                    try:
                        save(resized(get(url)), "RHS", page, url.rsplit("/", 1)[-1])
                    except Exception as e:
                        print("failed  ", name, "-", url, "-", e)
            except Exception as e:
                print("rhs page", name, "-", e)

        # 2. Wikimedia Commons top-up
        if len(entries) < MIN_TOTAL:
            for file_title, fallback in wiki_photos(genus, species, wiki):
                if len(entries) >= PER_SPECIES:
                    break
                try:
                    url, width, artist, licence = file_info(file_title)
                    if width and width < MIN_SOURCE:
                        continue
                    data = resized(get(url))
                except Exception as e:
                    print("failed  ", name, "-", file_title, "-", e)
                    continue
                page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(file_title)
                save(data, "Wikimedia Commons", page, file_title)
                credit_rows.append((name, entries[-1]["file"], file_title, artist, licence, page))
                if len(entries) >= MIN_TOTAL:
                    break

        if entries:
            index[slug] = entries
            for e in entries:
                if e["source"] == "RHS":
                    credit_rows.append((name, e["file"], e["title"], "Royal Horticultural Society", "© RHS, all rights reserved", e["page"]))
        else:
            print("no image", name)

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
    if credit_rows:
        path = os.path.join(OUT, "CREDITS.md")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write("# Photo credits\n\nRHS photos are reproduced from the RHS plant pages linked below and remain "
                        "the copyright of the Royal Horticultural Society. Wikimedia Commons photos are used under the "
                        "licence shown.\n\n")
            for name, fn, title, artist, licence, page in credit_rows:
                f.write(f"- **{name}** — `{fn}` — [{title}]({page}) — {artist or 'unknown author'} — {licence or 'see page'}\n")


if __name__ == "__main__":
    main()
