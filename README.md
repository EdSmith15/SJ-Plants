# Binomial Drill

A single-file flashcard app for learning plant species names (genus + species).
Open `index.html` in any browser, or add it to your phone's home screen.

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
Genus species | Common name | Family | https://example.com/optional-photo.jpg
```

Family and photo are optional. The deck is saved in the browser on that device.
The sample deck of 32 common UK plants is there as a placeholder; replace it with
your list.

## Photos

Each card shows an identifying photo above the common name. The app looks for
one in this order:

1. A photo URL given as the fourth field of the deck line.
2. `photos/<genus>-<species>.jpg` next to `index.html`.
3. The images on the species' English Wikipedia article, fetched live from
   Wikimedia and cached in the browser. The lead (taxobox) photo is shown first
   and up to four more from the article appear as thumbnails to tap through.

To keep photos with the repo for offline use, run:

```
python3 tools/fetch_photos.py
```

It saves an 800px copy of each lead photo into `photos/` and lists the source,
author and licence in `photos/CREDITS.md`. Pass a deck file as the first
argument to fetch photos for your own list.
