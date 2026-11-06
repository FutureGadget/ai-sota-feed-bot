"""Generate the branded share card, publisher logo, and site icons as PNGs.

One-time/occasional asset generator (not part of the hourly pipeline). The
outputs are committed static assets referenced by the site:

- ``web/og-default.png``        1200x630 default Open Graph / Twitter card
- ``web/logo.png``              512x512 "LD" monogram (schema.org publisher logo)
- ``web/icon-512.png``, ``web/icon-192.png``, ``web/apple-touch-icon.png``
                                full-bleed app icons (the rule mark)
- ``web/favicon-32.png``, ``web/favicon-16.png``, ``web/favicon.ico``
                                rounded tab icons (the rule mark)

``web/favicon.svg`` is the hand-authored vector of the same rule mark: a red
tile with three ruled lines, the mark the header draws in
``web/site-chrome.css`` (``.site-brand``). Keep its geometry in step with
``MARK_LINES`` below.

    python scripts/make_og_assets.py

Requires Pillow and the vendored Geist fonts (``assets/fonts/geist``).
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
    RULE,
    W,
    brand_mark,
    draw_text,
    face,
    fonts_available,
    wrap,
)

WEB = ROOT / "web"

BRAND = "LLM Digest"
# The feed masthead (web/index.html .feed-hero).
TITLE = "The daily paper for AI engineers."
TAGLINE = (
    "One shared ranking. Scan what changed, save what matters, "
    "and stop when the finish line appears."
)
AUDIENCE = "For platform and agent engineers"
URL = "llm-digest.com"

# Rule mark in the 512-unit favicon.svg viewBox: (x, y, width), 41 tall.
MARK_LINES = ((128, 154, 256), (128, 236, 256), (128, 318, 154))
MARK_LINE_H = 41


def rule_mark(size: int, *, rounded: bool) -> Image.Image:
    """The favicon's rule mark, drawn directly so every size is crisp."""
    scale = 4  # supersample, then downsize for smooth edges
    n = size * scale
    k = n / 512
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(128 * k) if rounded else 0
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=radius, fill=RED)
    for x, y, w in MARK_LINES:
        d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + MARK_LINE_H) * k], radius=20 * k, fill=PAPER)
    return img.resize((size, size), Image.LANCZOS)


def monogram(size: int) -> Image.Image:
    """The "LD" publisher logo: white Geist letters on the red tile."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.25), fill=RED)
    font = face("display", int(size * 0.46))
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

    brand_mark(d, MARGIN, 72, 56)
    draw_text(d, (MARGIN + 78, 74), BRAND, "display", 46, INK)
    d.line((MARGIN, 168, W - MARGIN, 168), fill=RULE, width=2)

    title_font = face("display", 76)
    y = 214
    for line in wrap(d, TITLE, title_font, W - 2 * MARGIN, 2):
        d.text((MARGIN, y), line, font=title_font, fill=INK)
        y += 84

    tag_font = face("text", 30)
    y += 30
    for line in wrap(d, TAGLINE, tag_font, W - 2 * MARGIN - 120, 2):
        d.text((MARGIN, y), line, font=tag_font, fill=MUTED)
        y += 42

    footer_y = H - 104
    d.line((MARGIN, footer_y, W - MARGIN, footer_y), fill=RULE, width=2)
    draw_text(d, (MARGIN, footer_y + 30), URL, "mono", 20, RED)
    draw_text(d, (W - MARGIN, footer_y + 30), AUDIENCE, "mono", 20, MUTED, align="right")
    return img


def main() -> None:
    if not fonts_available():
        raise SystemExit("Pillow and assets/fonts/geist/*.ttf are required")
    WEB.mkdir(parents=True, exist_ok=True)
    og_card().save(WEB / "og-default.png", optimize=True)
    monogram(512).save(WEB / "logo.png", optimize=True)
    for name, size in (("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180)):
        rule_mark(size, rounded=False).convert("RGB").save(WEB / name, optimize=True)
    for name, size in (("favicon-32.png", 32), ("favicon-16.png", 16)):
        rule_mark(size, rounded=True).save(WEB / name, optimize=True)
    rule_mark(64, rounded=True).save(WEB / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("wrote og-default.png, logo.png, icon-512/192, apple-touch-icon, favicon-32/16/.ico in web/")


if __name__ == "__main__":
    main()
