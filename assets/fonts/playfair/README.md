# Playfair (share-image fonts)

Static instances of [Playfair](https://github.com/clauseggers/Playfair)
(upstream commit `b869b3a`, SIL Open Font License 1.1, see `OFL.txt`), used
only to draw the Open Graph share images (`pipeline/og_cards.py`,
`scripts/make_og_assets.py`). Excluded from the Vercel deployment via
`.vercelignore`; the site itself uses system font stacks.

| File | Variable-font axes |
|---|---|
| `Playfair-DisplayBold.ttf` | opsz 72, wght 700, wdth 100 |
| `Playfair-TextRegular.ttf` | opsz 24, wght 400, wdth 100 |
| `Playfair-TextItalic.ttf` | opsz 24, wght 400, wdth 100 (italic) |

Each is subset to Latin, Latin-1 and general punctuation (dashes, quotes,
bullets, arrows) to keep the files small, and maps the digits to Playfair's
lining figures (`zero.lf`…) instead of its default old-style figures, so dates
and counts read at cap height. `build_fonts.py` regenerates all three from the
upstream `fonts/VF-TTF/*.ttf` (needs `fontTools`).
