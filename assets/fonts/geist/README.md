# Geist (share-image fonts)

Static instances of [Geist](https://github.com/vercel/geist-font) from the
`geist` npm package v1.9.2 (SIL Open Font License 1.1, see `OFL.txt`), used
only to draw the Open Graph share images and site icons
(`pipeline/og_cards.py`, `scripts/make_og_assets.py`). Never staged into
`public/`; the site serves its own variable copies from `web/fonts/`.

| File | Used for |
|---|---|
| `Geist-SemiBold.ttf` | brand name, headlines, the "LD" logo |
| `Geist-Regular.ttf` | one-line summaries, tagline |
| `GeistMono-Medium.ttf` | kicker, dateline, counts, URL |

Korean text falls back to Nanum Gothic from the workflows' `fonts-nanum`.
