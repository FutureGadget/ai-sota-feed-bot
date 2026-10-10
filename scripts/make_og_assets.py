"""Generate the branded share card, publisher logo, and site icons as PNGs.

One-time/occasional asset generator (not part of the hourly pipeline). The
outputs are committed static assets referenced by the site:

- ``web/og-default.png``        1200x630 default Open Graph / Twitter card
- ``web/logo.png``              512x512 "LD" monogram (schema.org publisher logo)
- ``web/icon-512.png``, ``web/icon-192.png``, ``web/apple-touch-icon.png``
                                full-bleed app icons (the stack mark)
- ``web/favicon-32.png``, ``web/favicon-16.png``, ``web/favicon.ico``
                                rounded tab icons (the stack mark)

``web/favicon.svg`` is the hand-authored vector of the same stack mark; keep
its colours in step with ``MARK_*`` below.

    python scripts/make_og_assets.py

Requires Pillow and the vendored Playfair fonts (``assets/fonts/playfair``).
Re-run after changing the brand colours, title, or tagline below. Drawing
helpers and the palette are shared with ``pipeline/og_cards.py`` so the default
card and the per-edition cards stay one design.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.og_cards import (  # noqa: E402
    H,
    INK,
    MARGIN,
    MUTED,
    PAPER,
    RED,
    W,
    double_rule,
    draw_label,
    fonts_available,
    serif,
    wrap,
)

WEB = ROOT / "web"

BRAND = "LLM Digest"
# The feed masthead and the line under it (web/index.html .feed-hero).
TITLE = "The daily paper for AI engineers."
TAGLINE = (
    "One shared ranking. Scan what changed, save what matters, "
    "and stop when the finish line appears."
)
AUDIENCE = "For platform & agent engineers"
URL = "llm-digest.com"

# Stack mark (web/favicon.svg): an ink-red tile, paper slabs, and a gold top
# slab for "today". Each slab is drawn with a darker copy offset below it.
MARK_TILE = RED
MARK_SLAB = PAPER
MARK_SLAB_SHADOW = (122, 35, 20)
MARK_TODAY = (224, 173, 78)
MARK_TODAY_SHADOW = (168, 111, 18)
# (x, y, width) in the 512-unit favicon.svg viewBox; every slab is 58 tall.
MARK_SLABS = ((204, 119, 104), (172, 191, 168), (139, 263, 234), (106, 335, 300))


def stack_mark(size: int, *, rounded: bool) -> Image.Image:
    """The favicon's stack mark, drawn directly so every size is crisp."""
    scale = 4  # supersample, then downsize for smooth edges
    n = size * scale
    k = n / 512
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(112 * k) if rounded else 0
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=radius, fill=MARK_TILE)
    for i, (x, y, w) in enumerate(MARK_SLABS):
        face, shadow = (MARK_TODAY, MARK_TODAY_SHADOW) if i == 0 else (MARK_SLAB, MARK_SLAB_SHADOW)
        r = 18 * k
        d.rounded_rectangle([x * k, (y + 12) * k, (x + w) * k, (y + 70) * k], radius=r, fill=shadow)
        d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + 58) * k], radius=r, fill=face)
    return img.resize((size, size), Image.LANCZOS)


def monogram(size: int) -> Image.Image:
    """The "LD" publisher logo: paper Playfair letters on an ink-red tile."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=RED)
    font = serif("display", int(size * 0.5))
    box = d.textbbox((0, 0), "LD", font=font)
    d.text(
        ((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
        "LD",
        font=font,
        fill=PAPER,
    )
    return img


def og_card() -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Nameplate.
    name_font = serif("display", 118)
    d.text(((W - d.textlength(BRAND, font=name_font)) / 2, 62), BRAND, font=name_font, fill=INK)
    double_rule(d, 230)

    title_font = serif("display", 62)
    d.text(((W - d.textlength(TITLE, font=title_font)) / 2, 272), TITLE, font=title_font, fill=INK)

    tag_font = serif("italic", 32)
    y = 372
    for line in wrap(d, TAGLINE, tag_font, W - 2 * MARGIN - 80, 2):
        d.text(((W - d.textlength(line, font=tag_font)) / 2, y), line, font=tag_font, fill=MUTED)
        y += 44

    footer_y = H - 110
    d.line((MARGIN, footer_y, W - MARGIN, footer_y), fill=INK, width=2)
    draw_label(d, (MARGIN, footer_y + 24), URL, 18, RED)
    aud_font = serif("italic", 26)
    d.text(
        (W - MARGIN - d.textlength(AUDIENCE, font=aud_font), footer_y + 18),
        AUDIENCE,
        font=aud_font,
        fill=MUTED,
    )
    return img


def main() -> None:
    if not fonts_available():
        raise SystemExit("Pillow and assets/fonts/playfair/*.ttf are required")
    WEB.mkdir(parents=True, exist_ok=True)
    og_card().save(WEB / "og-default.png", optimize=True)
    monogram(512).save(WEB / "logo.png", optimize=True)
    for name, size in (("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180)):
        stack_mark(size, rounded=False).convert("RGB").save(WEB / name, optimize=True)
    for name, size in (("favicon-32.png", 32), ("favicon-16.png", 16)):
        stack_mark(size, rounded=True).save(WEB / name, optimize=True)
    stack_mark(64, rounded=True).save(WEB / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("wrote og-default.png, logo.png, icon-512/192, apple-touch-icon, favicon-32/16/.ico in web/")


if __name__ == "__main__":
    main()
