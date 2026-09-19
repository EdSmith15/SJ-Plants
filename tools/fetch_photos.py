#!/usr/bin/env python3
"""Download one identifying photo per species into photos/ for offline use.

Usage:  python3 tools/fetch_photos.py            # uses the deck built into index.html
        python3 tools/fetch_photos.py deck.txt   # or any file in the Deck editor format

For each "Genus species" line it takes the lead image of the species' English
Wikipedia article (the taxobox photo, which is normally the classic
identification shot), saves a 800px copy as photos/<genus>-<species>.jpg and
records the source file, author and licence in photos/CREDITS.md.
Standard library only; needs internet access to en.wikipedia.org and
upload.wikimedia.org.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "photos")
UA = {"User-Agent": "BinomialDrill/1.0 (flashcard app; https://github.com/EdSmith15)"}
SKIP = re.compile(r"map|status|icon|logo|distribution|range|commons|wiki|question|edit|symbol", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def deck_lines(path=None):
    if path:
        text = open(path, encoding="utf-8").read()
    else:
        html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        m = re.search(r"var SAMPLE = \[(.*?)\]\.join", html, re.S)
        text = "\n".join(re.findall(r"'([^']*)'", m.group(1)))
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = ["×" if t in ("x", "X", "×") else t
                  for t in re.split(r"\s*(?:\||;|\t| - | – )\s*", line)[0].split()]
        if tokens and tokens[0] == "×":
            genus, rest = "× " + tokens[1].capitalize(), tokens[2:]
        else:
            genus, rest = tokens[0].capitalize(), tokens[1:]
        if [t for t in rest if t != "×"]:
            yield genus, " ".join(rest).lower()


def lead_image(genus, species):
    name = genus + " " + species
    titles = [name] + ([re.sub(r"× ?", "", name)] if "×" in name else [])
    data = {}
    for t in titles:
        try:
            data = json.loads(get("https://en.wikipedia.org/api/rest_v1/page/media-list/"
                                  + urllib.parse.quote(t.replace(" ", "_"))))
            break
        except Exception:
            continue
    items = [i for i in data.get("items", [])
             if i.get("type") == "image" and i.get("srcset")
             and not re.search(r"\.(svg|gif|png)$", i.get("title", ""), re.I)
             and not SKIP.search(i.get("title", ""))]
    items.sort(key=lambda i: not i.get("leadImage"))
    if not items:
        return None
    it = items[0]
    src = it["srcset"][0]["src"]
    if src.startswith("//"):
        src = "https:" + src
    src = re.sub(r"/\d+px-", "/800px-", src, count=1)
    return it["title"], src


def credit(file_title):
    q = urllib.parse.urlencode({
        "action": "query", "titles": file_title, "prop": "imageinfo",
        "iiprop": "extmetadata", "format": "json",
    })
    try:
        data = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
        page = next(iter(data["query"]["pages"].values()))
        meta = page["imageinfo"][0]["extmetadata"]
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        licence = meta.get("LicenseShortName", {}).get("value", "")
        return artist, licence
    except Exception:
        return "", ""


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for genus, species in deck_lines(sys.argv[1] if len(sys.argv) > 1 else None):
        slug = re.sub(r"[^a-z]+", "-", (genus + "-" + species).lower()).strip("-")
        dest = os.path.join(OUT, slug + ".jpg")
        name = genus + " " + species
        if os.path.exists(dest):
            print("kept    ", name)
            continue
        try:
            found = lead_image(genus, species)
            if not found:
                print("no image", name)
                continue
            file_title, src = found
            open(dest, "wb").write(get(src))
            artist, licence = credit(file_title)
            page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(file_title)
            rows.append((name, slug + ".jpg", file_title, artist, licence, page))
            print("saved   ", name, "<-", file_title)
        except Exception as e:  # keep going; report at the end
            print("failed  ", name, "-", e)
    if rows:
        with open(os.path.join(OUT, "CREDITS.md"), "a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write("# Photo credits\n\nAll photos from Wikimedia Commons under the licence shown.\n\n")
            for name, fn, ft, artist, licence, page in rows:
                f.write(f"- **{name}** — `{fn}` — [{ft}]({page}) — {artist or 'unknown author'} — {licence or 'see file page'}\n")


if __name__ == "__main__":
    main()
