"""Reader languages, read from ``config/locales.json``.

The first entry is the default edition (English, the source of truth). Every
other entry is a localized edition served under its ``path_prefix``. Adding a
language is one entry in that file plus its UI copy; no module branches on a
language code.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "locales.json"


@dataclass(frozen=True)
class Locale:
    code: str
    label: str
    path_prefix: str
    script: re.Pattern | None
    email: dict
    community: dict
    recap: dict
    dates: dict


def _load() -> dict[str, Locale]:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    out: dict[str, Locale] = {}
    for e in raw["locales"]:
        out[e["code"]] = Locale(
            code=e["code"],
            label=e["label"],
            path_prefix=e["path_prefix"],
            script=re.compile(e["script"]) if e.get("script") else None,
            email=e["email"],
            community=e["community"],
            recap=e["recap"],
            dates=e["dates"],
        )
    return out


_REGISTRY = _load()
LOCALES: tuple[str, ...] = tuple(_REGISTRY)
DEFAULT: str = LOCALES[0]


def get(code: str) -> Locale:
    return _REGISTRY[code]


def path(code: str, site_path: str) -> str:
    """Prefix a site path for a locale: ``/daily/x`` -> ``/ko/daily/x``."""
    return f"{_REGISTRY[code].path_prefix}{site_path}"


def others(code: str) -> tuple[str, ...]:
    return tuple(c for c in LOCALES if c != code)


def _fields(prefix: str, d: date, dates: dict) -> dict:
    return {
        f"{prefix}year": d.year,
        f"{prefix}month": d.month,
        f"{prefix}day": d.day,
        f"{prefix}mon": dates["months_short"][d.month - 1],
        f"{prefix}weekday_long": dates["weekdays_long"][d.weekday()],
        f"{prefix}weekday_short": dates["weekdays_short"][d.weekday()],
    }


def format_date(code: str, style: str, d: date) -> str:
    """One date in a locale's ``dates[style]`` pattern (long, short, header, edition)."""
    dates = _REGISTRY[code].dates
    return dates[style].format(**_fields("", d, dates))


def format_range(code: str, style: str, start: date, end: date) -> str:
    """A span in ``dates[<style>_same_month]`` or ``dates[<style>_cross_month]``."""
    dates = _REGISTRY[code].dates
    key = f"{style}_same_month" if start.month == end.month else f"{style}_cross_month"
    return dates[key].format(**_fields("", start, dates), **_fields("b_", end, dates))
