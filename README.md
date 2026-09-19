# SJ Plants

A single-file, iOS-styled flashcard app for learning plant species names
(genus + species). Live at https://edsmith15.github.io/SJ-Plants/ — open it in
Safari and use Share → Add to Home Screen. It opens with a welcome page, then a
level picker, then the cards.

The built-in deck is the **RHS Level 2 Certificate in Practical Horticulture,
PCA1 Plant List 2026/2027** (46 species, list numbers 1 to 110), with common
names and families taken from the RHS plant database. Hybrids such as
*Erica × darleyensis* show the × as a fixed character; in hard mode the × can be
typed as `x` or left out.

## Levels

| Level  | What you see                                   | What you type                         |
|--------|------------------------------------------------|---------------------------------------|
| Easy   | Both words with ~40% of the letters replaced by dashes. The blanked letters are re-rolled every time the card comes up. | The missing letters, one per dash |
| Medium | Either the genus or the species blanked out completely (chosen at random each time). | The whole missing word, one letter per dash |
| Hard   | Only the common name and family.               | The full name, e.g. `Quercus robur`   |

Every blank is shown as a dash. Input comes from the built-in iOS-style keyboard
(a physical keyboard also works on desktop). Cards you get wrong come back a few
cards later in the same round, and the round-end summary lists what to revisit.

## Your own species

Tap **Deck** in the top-left and paste one plant per line:

```
Genus species | Common name | Family | https://example.com/optional-photo.jpg | List number
```

Everything after the name is optional. Write hybrids with an `x` or `×`. The
deck is saved in the browser on that device; "Restore RHS list" brings back the
built-in deck.

## Photos

Each card shows an identifying photo above the common name. The app looks for
one in this order:

1. A photo URL given as the fourth field of the deck line.
2. `photos/<genus>-<species>.jpg`, `-2.jpg`, `-3.jpg`, `-4.jpg` next to `index.html`.
3. The images on the species' English Wikipedia article, fetched live from
   Wikimedia and cached in the browser. Write `wiki:Some title` in the fourth
   field to use a different article.

When there is more than one photo, swipe the picture or tap the thumbnails to
move through them, and tap the picture to enlarge it. Every card also links to
the RHS plant page for that species.

To keep photos with the repo for offline use, run:

```
python3 tools/fetch_photos.py
```

It downloads the original files from Wikimedia Commons, resizes them to at
most 1600px on the long side (needs `pip install pillow`), saves up to four per
species into `photos/` and lists the source, author and licence in
`photos/CREDITS.md`. Pass a deck file as the
first argument to fetch photos for your own list. The GitHub Actions workflow
in `.github/workflows/fetch-photos.yml` runs the same script automatically
whenever the deck changes and commits the results.
