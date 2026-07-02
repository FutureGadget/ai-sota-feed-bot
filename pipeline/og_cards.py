"""Per-edition Open Graph cards for the share surfaces (daily/weekly/storyline).

Every static page defaults to the one branded ``/og-default.png`` card, so a
shared recap or storyline unfurls indistinguishably from the homepage. This
module renders a 1200x630 card per edition — same brand system as
``scripts/make_og_assets.py`` (dark panel, accent rail, LD mark) plus the
edition's kicker, title, and stats — into ``web/og/<kind>-<ident>.png``.

Pillow is optional on purpose. The hourly feed workflow installs
``requirements.txt`` (which includes Pillow) and regenerates cards; the Vercel
build and the agent recap routines may not have Pillow, and must keep working:
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

# Brand palette, mirrored from scripts/make_og_assets.py.
ACCENT = (37, 99, 235)
BG = (21, 23, 28)
FG = (232, 232, 234)
MUTED = (154, 160, 170)
WHITE = (255, 255, 255)

BRAND = "LLM Digest"
URL = "llm-digest.com"

BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
REG_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

# Cards registered by ensure() this run; prune() keeps exactly these.
_keep: set[str] = set()


def _load_font(candidates: list[str], size: int):
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _logo(size: int):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=ACCENT)
    font = _load_font(BOLD_FONTS, int(size * 0.5))
    box = d.textbbox((0, 0), "LD", font=font)
    d.text(
        ((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
        "LD",
        font=font,
        fill=WHITE,
    )
    return img


def _wrap(d, text: str, font, max_w: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) > max_w and cur:
            lines.append(cur)
            cur = word
            if len(lines) == max_lines:
                break
        else:
            cur = trial
    if cur and len(lines) < max_lines:
        lines.append(cur)
    elif cur:
        # Ellipsize the last kept line when the title overflows.
        last = lines[-1]
        while last and d.textlength(last + "…", font=font) > max_w:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def _render_card(kicker: str, title: str, stats: str) -> bytes:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 16, h], fill=ACCENT)
    margin = 90

    logo = _logo(96)
    img.paste(logo, (margin, 70), logo)
    d.text((margin + 122, 90), BRAND, font=_load_font(BOLD_FONTS, 48), fill=WHITE)

    kicker_font = _load_font(BOLD_FONTS, 30)
    d.text((margin, 230), kicker.upper(), font=kicker_font, fill=ACCENT)

    title_font = _load_font(BOLD_FONTS, 64)
    y = 290
    for line in _wrap(d, title, title_font, w - 2 * margin, max_lines=3):
        d.text((margin, y), line, font=title_font, fill=FG)
        y += 80

    stats_font = _load_font(REG_FONTS, 32)
    d.text((margin, h - 140), stats, font=stats_font, fill=MUTED)
    d.text((margin, h - 84), URL, font=_load_font(REG_FONTS, 28), fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure(kind: str, ident: str, *, kicker: str, title: str, stats: str) -> str:
    """Return the site-relative card path for an edition, generating it if we can.

    Registers the card as live for prune(). Without Pillow, returns the
    committed card when present and "" (caller falls back to the default
    branded card) when not.
    """
    name = f"{kind}-{ident}.png"
    path = OG_DIR / name
    _keep.add(name)
    if HAVE_PIL:
        data = _render_card(kicker, title, stats)
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
