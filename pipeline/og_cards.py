"""Per-edition Open Graph cards for the share surfaces (daily/weekly/storyline).

Every static page defaults to the one branded ``/og-default.png`` card, so a
shared recap or storyline unfurls indistinguishably from the homepage. This
module renders a 1200x630 card per edition in the site's broadsheet style
(paper, ink, red kicker, Playfair headline; same system as
``scripts/make_og_assets.py``): nameplate and dateline, the edition's kicker,
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

# Broadsheet palette, mirrored from the light theme in web/site-chrome.css.
PAPER = (244, 240, 230)  # --bg
INK = (27, 24, 20)  # --fg
MUTED = (98, 90, 77)  # --muted
RED = (163, 48, 28)  # --accent
RULE = (214, 205, 187)  # --border

BRAND = "LLM Digest"
URL = "llm-digest.com"
W, H = 1200, 630
MARGIN = 72

# Vendored OFL serif (assets/fonts/playfair/README.md). Cards are only drawn
# when these exist, so an environment without them keeps the committed PNGs
# instead of writing cards in a fallback face.
FONT_DIR = ROOT / "assets" / "fonts" / "playfair"
DISPLAY_FONT = FONT_DIR / "Playfair-DisplayBold.ttf"
TEXT_FONT = FONT_DIR / "Playfair-TextRegular.ttf"
ITALIC_FONT = FONT_DIR / "Playfair-TextItalic.ttf"

# Small-caps labels (kicker, counts, URL) in a sans face the hosted runners ship.
LABEL_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]
# Playfair has no Hangul. Korean headlines and summaries use a Korean serif
# (Nanum Myeongjo ships in the fonts-nanum package the feed workflow installs);
# Korean labels use a Korean sans.
CJK_SERIF_BOLD_FONTS = [
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
    "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf",
]
CJK_SERIF_FONTS = [
    "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf",
    "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf",
]
CJK_BOLD_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    *LABEL_FONTS,
]
CJK_REG_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# Cards registered by ensure() this run; prune() keeps exactly these.
_keep: set[str] = set()


def fonts_available() -> bool:
    return HAVE_PIL and all(p.exists() for p in (DISPLAY_FONT, TEXT_FONT, ITALIC_FONT))


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


def serif(kind: str, size: int, text: str = ""):
    """Playfair for Latin text; a CJK face when the text needs one."""
    if _needs_cjk_font(text):
        if kind == "display":
            return _load_font([*CJK_SERIF_BOLD_FONTS, *CJK_BOLD_FONTS], size)
        return _load_font([*CJK_SERIF_FONTS, *CJK_REG_FONTS], size)
    path = {"display": DISPLAY_FONT, "italic": ITALIC_FONT}.get(kind, TEXT_FONT)
    return _load_font([path], size)


def label_font(size: int, text: str = ""):
    return _load_font(CJK_BOLD_FONTS if _needs_cjk_font(text) else LABEL_FONTS, size)


def draw_label(d, xy, text: str, size: int, fill, *, tracking: float = 0.18, align: str = "left") -> None:
    """Letterspaced caps, the site's kicker style."""
    text = text.upper()
    font = label_font(size, text)
    gap = size * tracking
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + gap * max(len(text) - 1, 0)
    x, y = xy
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2
    for ch, width in zip(text, widths):
        d.text((x, y), ch, font=font, fill=fill)
        x += width + gap


def double_rule(d, y: int, x0: int = MARGIN, x1: int = W - MARGIN) -> None:
    d.line((x0, y, x1, y), fill=INK, width=3)
    d.line((x0, y + 7, x1, y + 7), fill=INK, width=1)


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

    # Nameplate row: paper name left, dateline right, double rule under both.
    d.text((MARGIN, 40), BRAND, font=serif("display", 40), fill=INK)
    if dateline:
        date_font = serif("text", 24, dateline)
        d.text((W - MARGIN - d.textlength(dateline, font=date_font), 54), dateline, font=date_font, fill=MUTED)
    double_rule(d, 106)

    draw_label(d, (MARGIN, 146), kicker, 21, RED)

    footer_y = H - 110
    # Headline: as large as fits in two lines, else a smaller three.
    for size, max_lines in ((80, 2), (64, 3)):
        title_font = serif("display", size, title)
        lines = wrap(d, title, title_font, text_w, max_lines)
        if len(lines) < max_lines or max_lines == 3 or not lines[-1].endswith("…"):
            break
    line_h = int(size * 1.12)
    y = 186
    for line in lines:
        d.text((MARGIN, y), line, font=title_font, fill=INK)
        y += line_h

    # One-line summary under the headline, only where it fits above the footer.
    if dek:
        dek_font = serif("italic", 30, dek)
        dek_h = 42
        room = (footer_y - 24 - (y + 14)) // dek_h
        for line in wrap(d, dek, dek_font, text_w, max(0, min(2, room))):
            d.text((MARGIN, y + 14), line, font=dek_font, fill=MUTED)
            y += dek_h

    d.line((MARGIN, footer_y, W - MARGIN, footer_y), fill=INK, width=2)
    if stats:
        draw_label(d, (MARGIN, footer_y + 24), stats, 18, INK, tracking=0.14)
    draw_label(d, (W - MARGIN, footer_y + 24), URL, 18, RED, align="right")

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
