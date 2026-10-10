"""Rebuild the static Playfair instances used by the share images.

    python assets/fonts/playfair/build_fonts.py <upstream fonts/VF-TTF dir> assets/fonts/playfair

Needs fontTools (not a runtime dependency). See README.md in this directory.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
src, out = sys.argv[1], sys.argv[2]
UNICODES = "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+2010-2027,U+2030-203A,U+2190-2193,U+2212"
jobs = [
    ("PlayfairRomanVF.ttf", "Playfair-DisplayBold.ttf", {"opsz": 72, "wght": 700, "wdth": 100}, "Display Bold"),
    ("PlayfairRomanVF.ttf", "Playfair-TextRegular.ttf", {"opsz": 24, "wght": 400, "wdth": 100}, "Text Regular"),
    ("PlayfairItalicVF.ttf", "Playfair-TextItalic.ttf", {"opsz": 24, "wght": 400, "wdth": 100}, "Text Italic"),
]
for vf, name, axes, style in jobs:
    font = TTFont(f"{src}/{vf}")
    static = instancer.instantiateVariableFont(font, axes, updateFontNames=False)
    # Lining figures by default: Playfair maps digits to old-style glyphs.
    names = set(static.getGlyphOrder())
    for table in static["cmap"].tables:
        for cp in range(ord("0"), ord("9") + 1):
            if cp in table.cmap and table.cmap[cp] + ".lf" in names:
                table.cmap[cp] = table.cmap[cp] + ".lf"
    opts = subset.Options(); opts.layout_features = ["kern", "liga", "lnum", "pnum"]; opts.name_IDs = ["*"]; opts.notdef_outline = True
    sub = subset.Subsetter(opts); sub.populate(unicodes=subset.parse_unicodes(UNICODES)); sub.subset(static)
    # Name the instance so it is distinguishable from the upstream variable font.
    for rec in static["name"].names:
        if rec.nameID in (2, 17):
            rec.string = style
    static.save(f"{out}/{name}")
