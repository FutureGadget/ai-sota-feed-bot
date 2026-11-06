"""Per-edition Open Graph cards for the share surfaces (daily/weekly/storyline).

Every static page defaults to the one branded ``/og-default.png`` card, so a
shared recap or storyline unfurls indistinguishably from the homepage. This
module renders a 1200x630 card per edition in the site's Precision style
(white paper, near-black ink, one red accent, Geist type; same system as
``scripts/make_og_assets.py``): brand mark and dateline, the edition's kicker,
title, a one-line summary, and counts — into ``web/og/<kind>-<ident>.png``.

Pillow and the vendored fonts are optional on purpose. The hourly feed
workflow installs ``requirements.txt`` (which includes Pillow) and regenerates
cards; the Vercel build and the agent recap routines may not have Pillow, and
must keep working:
``ensure()`` then simply points at the committed PNG when one exists and falls
back to the default card ("") when it doesn't. A missing card self-heals on the
next hourly run because ``render_static_pages.py`` re-renders every page.

Writes are byte-stable (only rewritten when content changes) so hourly runs
don't churn git with identical PNGs. ``prune()`` removes cards whose edition
no longer renders, mirroring the static-page orphan pruning.
"""

from __future__ import annotations

import io
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont

    HAVE_PIL = True
except ImportError:  # pragma: no cover - environment-dependent
    HAVE_PIL = False

ROOT = Path(__file__).resolve().parents[1]
OG_DIR = ROOT / "web" / "og"

# Precision palette, mirrored from the light theme in web/site-chrome.css.
PAPER = (255, 255, 255)  # --bg
INK = (24, 24, 27)  # --fg
MUTED = (98, 98, 107)  # --muted
RED = (208, 38, 45)  # --accent
RULE = (228, 228, 231)  # --border

BRAND = "LLM Digest"
URL = "llm-digest.com"
W, H = 1200, 630
MARGIN = 72

# Vendored OFL Geist (assets/fonts/geist/README.md), the site's own face.
# Cards are only drawn when these exist, so an environment without them keeps
# the committed PNGs instead of writing cards in a fallback face.
FONT_DIR = ROOT / "assets" / "fonts" / "geist"
DISPLAY_FONT = FONT_DIR / "Geist-SemiBold.ttf"
TEXT_FONT = FONT_DIR / "Geist-Regular.ttf"
MONO_FONT = FONT_DIR / "GeistMono-Medium.ttf"

# Geist has no Hangul. Korean text uses Nanum Gothic (the fonts-nanum package
# the feed workflow installs) or a system Korean sans.
CJK_BOLD_FONTS = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]
CJK_REG_FONTS = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

# Cards registered by ensure() this run; prune() keeps exactly these.
_keep: set[str] = set()


def fonts_available() -> bool:
    return HAVE_PIL and all(p.exists() for p in (DISPLAY_FONT, TEXT_FONT, MONO_FONT))


def _load_font(candidates, size: int):
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _needs_cjk_font(*values: str) -> bool:
    return any(any(ord(ch) > 0x2FFF for ch in str(value or "")) for value in values)


def face(kind: str, size: int, text: str = ""):
    """Geist for Latin text ("display" semibold, "text" regular, "mono");
    a Korean sans when the text needs one."""
    if _needs_cjk_font(text):
        return _load_font(CJK_BOLD_FONTS if kind == "display" else CJK_REG_FONTS, size)
    path = {"display": DISPLAY_FONT, "mono": MONO_FONT}.get(kind, TEXT_FONT)
    return _load_font([path], size)


def draw_text(d, xy, text: str, kind: str, size: int, fill, *, align: str = "left") -> None:
    font = face(kind, size, text)
    x, y = xy
    if align == "right":
        x -= d.textlength(text, font=font)
    d.text((x, y), text, font=font, fill=fill)


def brand_mark(d, x: int, y: int, size: int) -> None:
    """The site's brand mark: a red tile with three ruled lines
    (web/favicon.svg, .site-brand in web/site-chrome.css)."""
    k = size / 20
    d.rounded_rectangle([x, y, x + size, y + size], radius=round(5 * k), fill=RED)
    for top, width in ((6, 10), (9.2, 10), (12.4, 6)):
        d.rounded_rectangle(
            [x + 5 * k, y + top * k, x + (5 + width) * k, y + (top + 1.6) * k],
            radius=max(1, round(0.8 * k)),
            fill=PAPER,
        )


def wrap(d, text: str, font, max_w: int, max_lines: int) -> list[str]:
    """Greedy word wrap; CJK text without spaces wraps by character."""
    words = text.split()
    if _needs_cjk_font(text) and any(d.textlength(w, font=font) > max_w for w in words):
        words = list(text)
    lines: list[str] = []
    cur = ""
    overflow = False
    for word in words:
        sep = "" if len(word) == 1 and _needs_cjk_font(word) else " "
        trial = (cur + sep + word).strip() if cur else word
        if d.textlength(trial, font=font) > max_w and cur:
            lines.append(cur)
            cur = word
            if len(lines) == max_lines:
                overflow = True
                break
        else:
            cur = trial
    if cur and not overflow:
        lines.append(cur)
    elif lines:
        # Ellipsize the last kept line when the text overflows.
        last = lines[-1]
        while last and d.textlength(last + "…", font=font) > max_w:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def _render_card(kicker: str, title: str, stats: str, *, dateline: str = "", dek: str = "") -> bytes:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    text_w = W - 2 * MARGIN

    # Brand row: mark and name left, dateline right, one hairline under both.
    brand_mark(d, MARGIN, 52, 40)
    draw_text(d, (MARGIN + 56, 52), BRAND, "display", 34, INK)
    if dateline:
        draw_text(d, (W - MARGIN, 62), dateline, "mono", 22, MUTED, align="right")
    d.line((MARGIN, 120, W - MARGIN, 120), fill=RULE, width=2)

    draw_text(d, (MARGIN, 158), kicker, "mono", 24, RED)

    footer_y = H - 104
    # Headline: as large as fits in two lines, else a smaller three.
    for size, max_lines in ((78, 2), (62, 3)):
        title_font = face("display", size, title)
        lines = wrap(d, title, title_font, text_w, max_lines)
        if len(lines) < max_lines or max_lines == 3 or not lines[-1].endswith("…"):
            break
    line_h = int(size * 1.1)
    y = 204
    for line in lines:
        d.text((MARGIN, y), line, font=title_font, fill=INK)
        y += line_h

    # One-line summary under the headline, only where it fits above the footer.
    if dek:
        dek_font = face("text", 30, dek)
        dek_h = 42
        room = (footer_y - 24 - (y + 28)) // dek_h
        for line in wrap(d, dek, dek_font, text_w, max(0, min(2, room))):
            d.text((MARGIN, y + 28), line, font=dek_font, fill=MUTED)
            y += dek_h

    d.line((MARGIN, footer_y, W - MARGIN, footer_y), fill=RULE, width=2)
    if stats:
        draw_text(d, (MARGIN, footer_y + 30), stats, "mono", 20, MUTED)
    draw_text(d, (W - MARGIN, footer_y + 30), URL, "mono", 20, RED, align="right")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure(
    kind: str,
    ident: str,
    *,
    kicker: str,
    title: str,
    stats: str,
    dateline: str = "",
    dek: str = "",
    locale: str = "",
) -> str:
    """Return the site-relative card path for an edition, generating it if we can.

    Registers the card as live for prune(). Without Pillow or the vendored
    fonts, returns the committed card when present and "" (caller falls back
    to the default branded card) when not.
    """
    locale_suffix = f"-{locale}" if locale else ""
    name = f"{kind}-{ident}{locale_suffix}.png"
    path = OG_DIR / name
    _keep.add(name)
    if fonts_available():
        data = _render_card(kicker, title, stats, dateline=dateline, dek=dek)
        if not path.exists() or path.read_bytes() != data:
            OG_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print(f"og card written: {path.relative_to(ROOT)}")
    return f"/og/{name}" if path.exists() else ""


def prune() -> None:
    """Delete cards whose edition was not registered this run."""
    if not OG_DIR.is_dir():
        return
    for path in OG_DIR.glob("*.png"):
        if path.name not in _keep:
            path.unlink()
            print(f"pruned stale og card: {path.relative_to(ROOT)}")
