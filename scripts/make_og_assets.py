"""Generate the branded social-share card and publisher logo as PNGs.

One-time/occasional asset generator (not part of the hourly pipeline). The
outputs are committed static assets referenced by the site:

- ``web/og-default.png``  1200x630 default Open Graph / Twitter card
- ``web/logo.png``        512x512 square logo (schema.org publisher logo)

``web/favicon.svg`` is hand-authored (vector) and not produced here.

    python scripts/make_og_assets.py

Requires Pillow (already a dev dependency of the repo's tooling environment).
Re-run after changing the brand colors or tagline below.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

ACCENT = (37, 99, 235)      # --accent
BG = (21, 23, 28)           # --bg (dark)
FG = (232, 232, 234)        # --fg (dark)
MUTED = (154, 160, 170)     # --muted (dark)
WHITE = (255, 255, 255)

BRAND = "LLM Digest"
TAGLINE = "The finishable AI feed for platform engineers"
URL = "llm-digest.com"

# macOS / common font locations, bold then regular candidates.
BOLD_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
REG_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def rounded_logo(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=ACCENT)
    font = load_font(BOLD_FONTS, int(size * 0.5))
    text = "LD"
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(
        ((size - tw) / 2 - box[0], (size - th) / 2 - box[1]),
        text,
        font=font,
        fill=WHITE,
    )
    return img


def og_card() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    # Accent left rail.
    d.rectangle([0, 0, 16, h], fill=ACCENT)
    margin = 90
    # Logo top-left.
    logo = rounded_logo(120)
    img.paste(logo, (margin, 80), logo)
    # Brand wordmark next to logo.
    brand_font = load_font(BOLD_FONTS, 56)
    d.text((margin + 150, 96), BRAND, font=brand_font, fill=WHITE)
    # Tagline (the value prop), large, possibly two lines.
    tag_font = load_font(BOLD_FONTS, 72)
    words = TAGLINE.split()
    lines, cur = [], ""
    max_w = w - 2 * margin
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=tag_font) > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    y = 300
    for line in lines:
        d.text((margin, y), line, font=tag_font, fill=FG)
        y += 90
    # URL footer.
    url_font = load_font(REG_FONTS, 36)
    d.text((margin, h - 90), URL, font=url_font, fill=MUTED)
    return img


def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    rounded_logo(512).save(WEB / "logo.png")
    og_card().save(WEB / "og-default.png")
    print(f"wrote {WEB / 'logo.png'} and {WEB / 'og-default.png'}")


if __name__ == "__main__":
    main()
