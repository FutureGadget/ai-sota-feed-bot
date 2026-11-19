#!/usr/bin/env python3
"""Email digest publisher — daily finishable brief to the subscriber list.

Uses committed artifacts as input and a secrets-gated no-op contract
(no ``EMAIL_API_KEY`` => render nothing, send
nothing, touch no state). A third-party newsletter provider (Buttondown or
Resend) owns the subscriber list, double-opt-in, unsubscribe and compliance —
no subscriber PII ever lives in this repo. We only hold an API key in env and
POST a rendered broadcast.

The daily brief carries the **curated daily recap** (``data/daily/latest.json`` —
the very same editorial recap the ``/daily`` page serves: an intro, highlights,
and themed categories) so the email and the page show the same content, plus a
"Continuing threads" block of storylines that **moved since the last send**.
That delta is computed against a committed cursor (``data/email/state.json``,
mirroring ``data/health/alerts_state.json``) using the *content-based* storyline
signal ``last_updated`` — never ``generated_at``, which the 5-hourly rebuild
bumps every run (see ``api/updates.js`` for the same pattern).

The daily idempotency guard keys off the **recap's own date**, not the calendar
day: the email sends the latest committed recap once and re-sends only when a
newer recap appears (no new recap ⇒ clean no-op, never the raw feed).

Usage:
    python3 publish/publish_email.py --kind daily            # send (if configured)
    python3 publish/publish_email.py --kind daily --dry-run  # render to stdout only
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.build_skill_lab import (  # noqa: E402
    build_store as validate_skill_lab_store,
    validate_record as validate_skill_lab_record,
)
from pipeline.story_store import story_sid  # noqa: E402
sys.path.insert(0, str(ROOT / "pipeline"))
import community  # noqa: E402
import recap_i18n  # noqa: E402
from source_labels import SOURCE_ACRONYMS, SOURCE_NAMES, source_name  # noqa: E402,F401

STATE_PATH = ROOT / "data" / "email" / "state.json"
SKILL_LAB_DIR = ROOT / "data" / "playbook" / "lab"
SKILL_LAB_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
SKILL_LAB_ID_RE = re.compile(r"^lab-[a-z0-9][a-z0-9-]{0,76}$")
SKILL_LAB_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SKILL_LAB_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SKILL_LAB_SUMMARY_FIELDS = (
    "schema_version",
    "id",
    "slug",
    "pilot_edition",
    "pilot_size",
    "state",
    "date",
    "generated_at",
    "featured_until",
    "title",
    "question",
    "summary",
)
DEFAULTS = {
    "enabled": False,
    "provider": "buttondown",
    "from_name": "LLM Digest",
    "site_base": "https://www.llm-digest.com",
    "utm_source": "email",
    "daily": {"max_items": 12, "max_threads": 3, "full_items_per_theme": 2},
    "weekly": {"max_threads": 12, "articles_per_category": 3, "max_wiki": 4, "max_favorites": 3},
}

# Invisible filler appended after the preheader so the body's first visible line
# doesn't bleed into the inbox preview after the snippet (the standard hack:
# zero-width joiners + non-breaking spaces, which render as nothing).
PREHEADER_PAD = "&#847;&zwnj;&nbsp;" * 40


# --------------------------------------------------------------------------- #
# Locale copy. The English recap is the source of truth; the Korean email reads
# the agent-written translation (data/i18n/ko/<kind>/<id>.json) and these labels.
# --------------------------------------------------------------------------- #
LOCALES = ("en", "ko")
EMAIL_COPY = {
    "en": {
        "daily_subject": "{top} · {n} picks, ~{mins} min",
        "weekly_subject": "{top} · Your AI week, {range}",
        "daily_h1": "Your AI brief",
        "daily_meta": "{n} picks · {cats} theme{s} · ~{mins} min · one shared ranking, no filter bubble",
        "tldr": "In 30 seconds",
        "video_daily": "Watch the 2-minute explainer",
        "video_weekly": "Watch the weekly explainer",
        "theme": "Theme {idx} · {n} {items}",
        "item": "item",
        "items": "items",
        "threads_daily": "🧵 Storylines that moved today",
        "threads_daily_dek": "Ongoing stories with a new development since the last brief.",
        "storyline_meta": "Storyline · {n} stories over {d} days",
        "caught_up": "✅ You're caught up.",
        "web": "Read this on the web",
        "feed": "Open the full feed",
        "week_link": "This week's recap",
        "tagline": "The finishable AI feed for platform engineers — 10 minutes a day, with memory.",
        "useful": "👍 Useful",
        "useful_short": "👍",
        "irrelevant_short": "👎",
        "irrelevant": "👎 Not relevant",
        "unsubscribe": "Manage preferences or unsubscribe",
        "why": "You're getting this because you subscribed at llm-digest.com.",
        "share": "Know someone who'd want this? Forward it →",
        "share_subject": "Worth a read: {title}",
        "share_body": "Today's AI brief from LLM Digest: {url}\n\nGet it by email: {sub}",
        "more_in_theme": "Also in this theme",
        "switch_lang": "이 메일을 한국어로 받기",
        "preheader_tail": " — then you're caught up.",
        "more": " · +{n} more",
        "weekly_header": "LLM Digest · Weekly recap",
        "weekly_highlights": "⭐ Highlights",
        "favorites": "📈 <strong>Reader favorites this week</strong> — sources you clicked most: {chips}",
        "by_theme": "📚 By theme",
        "threads_weekly": "🧵 Storylines that moved this week",
        "wiki": "🪐 New agent know-how",
        "wiki_dek": "Patterns and solutions that emerged this week — the durable layer, not the news.",
        "obstacle": "obstacle",
        "solution": "solution",
        "full_recap": "Read the full recap",
        "open_feed": "Open the feed",
        "weekly_preheader_tail": " — your weekly catch-up.",
        "community": "💬 From the community",
        "community_meta": "The agent that writes this brief, on {period}'s news · {n} comments",
        "period_daily": "today",
        "period_weekly": "this week",
        "read_thread": "Read the thread →",
    },
    "ko": {
        "daily_subject": "{top} · {n}개, 약 {mins}분",
        "weekly_subject": "{top} · AI 위클리 {range}",
        "daily_h1": "오늘의 AI 브리프",
        "daily_meta": "{n}개 · 테마 {cats}개 · 약 {mins}분 · 모두에게 같은 랭킹, 필터 버블 없음",
        "tldr": "30초 요약",
        "video_daily": "2분 설명 영상 보기",
        "video_weekly": "주간 설명 영상 보기",
        "theme": "테마 {idx} · {n}건",
        "item": "건",
        "items": "건",
        "threads_daily": "🧵 오늘 움직인 스토리",
        "threads_daily_dek": "지난 브리프 이후 새 소식이 생긴 진행 중인 이야기입니다.",
        "storyline_meta": "스토리 · {d}일간 {n}건",
        "caught_up": "✅ 오늘 브리프는 여기까지입니다.",
        "web": "웹에서 보기",
        "feed": "전체 피드 열기",
        "week_link": "이번 주 리캡",
        "tagline": "플랫폼·에이전트 엔지니어를 위한 끝이 있는 AI 피드 — 하루 10분, 맥락까지.",
        "useful": "👍 유용함",
        "useful_short": "👍",
        "irrelevant_short": "👎",
        "irrelevant": "👎 관련 없음",
        "unsubscribe": "수신 설정 · 수신 거부",
        "why": "llm-digest.com에서 구독하셔서 받는 메일입니다.",
        "share": "이 브리프가 필요한 동료가 있나요? 전달하기 →",
        "share_subject": "읽어볼 만한 AI 브리프: {title}",
        "share_body": "LLM Digest의 오늘 AI 브리프: {url}\n\n이메일로 받기: {sub}",
        "more_in_theme": "이 테마의 다른 소식",
        "switch_lang": "Get this email in English",
        "preheader_tail": " — 읽고 나면 끝.",
        "more": " · 외 {n}건",
        "weekly_header": "LLM Digest · 위클리 리캡",
        "weekly_highlights": "⭐ 이번 주 핵심",
        "favorites": "📈 <strong>이번 주 독자 인기 출처</strong> — 가장 많이 클릭한 출처: {chips}",
        "by_theme": "📚 테마별",
        "threads_weekly": "🧵 이번 주 움직인 스토리",
        "wiki": "🪐 새 에이전트 노하우",
        "wiki_dek": "이번 주에 정리된 패턴과 해법 — 뉴스가 아니라 오래 남는 지식입니다.",
        "obstacle": "문제",
        "solution": "해법",
        "full_recap": "전체 리캡 보기",
        "open_feed": "피드 열기",
        "weekly_preheader_tail": " — 이번 주 따라잡기.",
        "community": "💬 커뮤니티에서",
        "community_meta": "이 브리프를 쓰는 에이전트의 {period} 이야기 · 댓글 {n}개",
        "period_daily": "오늘",
        "period_weekly": "이번 주",
        "read_thread": "스레드 보기 →",
    },
}


def _t(locale: str, key: str, **kw) -> str:
    text = EMAIL_COPY.get(locale, EMAIL_COPY["en"]).get(key) or EMAIL_COPY["en"][key]
    return text.format(**kw) if kw else text


def site_path(locale: str, path: str) -> str:
    """Prefix a site path for a locale: ``/daily/x`` -> ``/ko/daily/x``."""
    return f"/ko{path}" if locale == "ko" else path


def _fresh_i18n(surface: str, ident: str, source: dict | None, locale: str) -> dict | None:
    """A fresh translation artifact for one storyline/topic, or None."""
    if locale == "en" or not isinstance(source, dict):
        return None
    path = ROOT / "data" / "i18n" / locale / surface / f"{ident}.json"
    if not path.exists():
        return None
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not recap_i18n.render.i18n_hash_matches(artifact.get("source_hash"), source):
        return None
    return artifact


def localize_threads(threads: list[dict], locale: str) -> list[dict]:
    """Storyline rows with a fresh translated label/what's-new; English otherwise."""
    if locale == "en":
        return threads
    out = []
    for t in threads:
        row = dict(t)
        detail_path = ROOT / "data" / "storylines" / f"{t.get('slug', '')}.json"
        try:
            detail = json.loads(detail_path.read_text(encoding="utf-8")) if detail_path.exists() else None
        except Exception:
            detail = None
        artifact = _fresh_i18n("storyline", str(t.get("slug") or ""), detail, locale)
        if artifact:
            row["label"] = artifact.get("label") or row["label"]
            editorial = artifact.get("editorial") if isinstance(artifact.get("editorial"), dict) else {}
            if editorial.get("whats_new"):
                row["whats_new"] = editorial["whats_new"]
            row["localized"] = True
        out.append(row)
    return out


def localize_wiki(wiki: list[dict], locale: str) -> list[dict]:
    if locale == "en":
        return wiki
    try:
        nodes = (json.loads((ROOT / "data" / "wiki" / "index.json").read_text(encoding="utf-8")).get("nodes") or {})
    except Exception:
        nodes = {}
    out = []
    for w in wiki:
        row = dict(w)
        artifact = _fresh_i18n("topic", str(w.get("slug") or ""), nodes.get(w.get("slug")), locale)
        if artifact:
            row["title"] = artifact.get("title") or row["title"]
            row["summary"] = artifact.get("description") or row["summary"]
            row["localized"] = True
        out.append(row)
    return out


def clean(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    cut = s[: n - 1].rstrip()
    # Prefer the last word boundary so we never slice mid-word ("to understa…"),
    # but only if it doesn't chop off so much that the snippet loses its point.
    sp = cut.rfind(" ")
    if sp >= int(n * 0.6):
        cut = cut[:sp].rstrip()
    return cut.rstrip(" ,.;:–—-") + "…"


# Reader-facing publisher names, mirroring web/index.html's SOURCE_NAMES so the
# email and the site label sources identically. Unknown slugs degrade to an
# acronym-aware prettify (same fallback as the site's sourceDisplayName).
# Source display names live in pipeline/source_labels.py (shared with the pages).


# --------------------------------------------------------------------------- #
# Config + cursor state
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    cfg = dict(DEFAULTS)
    p = ROOT / "config" / "email.yaml"
    if p.exists():
        try:
            loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            cfg.update(loaded)
            for k in ("daily", "weekly"):
                if isinstance(loaded.get(k), dict):
                    cfg[k] = {**DEFAULTS[k], **loaded[k]}
        except Exception:
            pass
    return cfg


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Item + storyline rendering
# --------------------------------------------------------------------------- #
def story_url(cfg: dict, url: str) -> str:
    sid = story_sid(url)
    return f"{cfg['site_base'].rstrip('/')}/story/{sid}?utm_source={cfg['utm_source']}"


def storyline_url(cfg: dict, slug: str, locale: str = "en") -> str:
    return f"{cfg['site_base'].rstrip('/')}{site_path(locale, f'/storyline/{slug}')}?utm_source={cfg['utm_source']}"


def feedback_url(cfg: dict, url: str, signal: str) -> str:
    """One-tap feedback deep link: lands on the feed with the item highlighted
    and ``?fb=<signal>``, which the client records as the same ``item_feedback``
    event the on-page buttons fire (synced into the auto-tune loop). No new
    endpoint — it reuses the existing share-landing ``?item=<url>`` path.
    """
    base = cfg["site_base"].rstrip("/")
    return f"{base}/?item={quote(url, safe='')}&fb={signal}&utm_source={cfg['utm_source']}"


# Per-subscriber reader id (Resend contact property). Email clicks often open in
# a mail app's in-app browser with a fresh anonymous id, so without this every
# email visit looks like a new reader. `api/subscribe.js` stores the signup
# browser's anonymous id as the contact's `reader_id`; broadcasts template it
# into every on-site link as `rid=`, and `web/posthog-client.js` adopts it (then
# strips it from the URL). The fallback is a sentinel the client rejects.
READER_ID_PROPERTY = "reader_id"
READER_ID_FALLBACK = "none"
READER_ID_TOKEN = "{{{contact.%s|%s}}}" % (READER_ID_PROPERTY, READER_ID_FALLBACK)


def video_link_html(cfg: dict, recap: dict, page_path: str, label: str) -> str:
    """A "watch the explainer" link to the recap page's #video anchor, or ""
    when the recap has no valid ``video``. Never embeds the video."""
    video = recap.get("video")
    if not (isinstance(video, dict) and re.fullmatch(r"[A-Za-z0-9_-]{11}", str(video.get("youtube_id") or ""))):
        return ""
    url = f"{cfg['site_base'].rstrip('/')}{page_path}?utm_source={cfg['utm_source']}&utm_content=video#video"
    return (
        '<div style="margin:0 0 14px;font-size:16px">'
        f'<a href="{html.escape(url)}" style="color:#1a6dd6;font-weight:600">▶ {html.escape(label)}</a></div>'
    )


def with_utm(cfg: dict, body: str, **params: str) -> str:
    """Add ``utm_*`` parameters to every tracked on-site link (one that already
    carries ``utm_source``) that does not set them yet. Fragments stay last."""
    base = re.escape(cfg["site_base"].rstrip("/"))

    def repl(m: re.Match) -> str:
        url, hash_, frag = m.group(1).partition("#")
        add = "".join(
            f"&amp;{key}={quote(str(value), safe='')}"
            for key, value in params.items()
            if value and not re.search(rf"[?&](?:amp;)?{key}=", url)
        )
        return f'href="{url}{add}{hash_}{frag}"'

    return re.sub(rf'href="({base}/[^"]*[?&](?:amp;)?utm_source=[^"]*)"', repl, body)


def tag_reader_links(cfg: dict, body: str) -> str:
    """Append ``rid=<per-contact token>`` to every on-site link that already
    carries ``utm_source`` (i.e. every tracked link we render). Idempotent."""
    base = re.escape(cfg["site_base"].rstrip("/"))

    def repl(m: re.Match) -> str:
        href = m.group(1)
        if re.search(r"[?&](?:amp;)?rid=", href):
            return m.group(0)
        # Keep any #fragment last so anchors such as #video still resolve.
        url, hash_, frag = href.partition("#")
        return f'href="{url}&amp;rid={READER_ID_TOKEN}{hash_}{frag}"'

    return re.sub(rf'href="({base}/[^"]*[?&](?:amp;)?utm_source=[^"]*)"', repl, body)


def ensure_reader_id_property(api_key: str) -> bool:
    """Make sure the Resend ``reader_id`` contact property exists so the
    broadcast's ``{{{contact.reader_id|none}}}`` token resolves. Returns False
    (send untagged links) on any failure — never blocks the send."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get("https://api.resend.com/contact-properties", headers=headers, timeout=30)
        r.raise_for_status()
        if any((p or {}).get("key") == READER_ID_PROPERTY for p in r.json().get("data") or []):
            return True
        r = requests.post(
            "https://api.resend.com/contact-properties",
            headers=headers,
            json={"key": READER_ID_PROPERTY, "type": "string", "fallback_value": READER_ID_FALLBACK},
            timeout=30,
        )
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001 — optional attribution, never fatal
        print(f"email_reader_id_property_unavailable=true error={type(e).__name__}")
        return False


def feedback_links(cfg: dict, url: str, locale: str = "en", short: bool = False) -> str:
    """One-tap 👍 / 👎 links that sit on an item's source line (no row of their
    own). ``short`` drops the words for the compact headline rows; the full
    label stays as the link title."""
    if not url:
        return ""
    useful = html.escape(feedback_url(cfg, url, "useful"))
    irrel = html.escape(feedback_url(cfg, url, "irrelevant"))
    up, down = _t(locale, "useful"), _t(locale, "irrelevant")
    up_text = _t(locale, "useful_short") if short else up
    down_text = _t(locale, "irrelevant_short") if short else down
    return (
        '<span class="ld-fb"> · '
        f'<a href="{useful}" title="{html.escape(up)}" style="color:#1a7f37;text-decoration:none">{up_text}</a>'
        " · "
        f'<a href="{irrel}" title="{html.escape(down)}" style="color:#999;text-decoration:none">{down_text}</a>'
        "</span>"
    )


def daily_articles(recap: dict) -> list[dict]:
    """Flatten the recap's category articles in display order."""
    out: list[dict] = []
    for c in recap.get("categories") or []:
        if not isinstance(c, dict):
            continue
        for a in c.get("articles") or []:
            if isinstance(a, dict):
                out.append(a)
    return out


def _preheader(recap: dict, articles: list[dict], locale: str = "en") -> str:
    """Inbox-preview snippet: lead with the recap's first highlight (its editorial
    "in 30 seconds"), else the top headlines + remaining count — so the brief
    sells itself in the inbox instead of leaking the boilerplate header.
    """
    highlights = [clean(h, 90) for h in (recap.get("highlights") or []) if isinstance(h, str) and h.strip()]
    if highlights:
        return f"{highlights[0]}{_t(locale, 'preheader_tail')}"
    titles = [clean(a.get("title", ""), 50) for a in articles[:2] if a.get("title")]
    extra = max(0, len(articles) - len(titles))
    tail = _t(locale, "more", n=extra) if extra else ""
    return f"{' · '.join(titles)}{tail}{_t(locale, 'preheader_tail')}"


def reader_favorites(limit: int = 3) -> list[tuple[str, int]]:
    """Top sources by click-through in the rolling CTR window (the same
    source-level signal that drives auto-tune). Per-article click data is not
    collected, so this is honest social proof at *source* granularity — matching
    how the rest of the email already labels items by source slug.
    """
    p = ROOT / "data" / "feedback" / "ctr_clicks.json"
    if not p.exists():
        return []
    try:
        clicks = json.loads(p.read_text(encoding="utf-8")).get("clicks") or {}
    except Exception:
        return []
    ranked = sorted(
        ((s, int(c)) for s, c in clicks.items() if int(c) > 0),
        key=lambda r: r[1],
        reverse=True,
    )
    return ranked[:limit]


def narrative_copy(slug: str, thread_last_updated: str, latest_title: str) -> str:
    """Narration-lag guard: only use the sidecar ``whats_new`` when the editor
    routine has caught up to the thread (``covers_last_updated`` is current).
    Otherwise fall back to the latest item title rather than ship a "new" badge
    over a stale narrative (the editor routine trails the thread by up to 5h).
    """
    p = ROOT / "data" / "storylines" / "narratives" / f"{slug}.json"
    if p.exists():
        try:
            n = json.loads(p.read_text(encoding="utf-8"))
            if (n.get("covers_last_updated") or "") >= thread_last_updated:
                wn = (n.get("whats_new") or "").strip()
                if wn:
                    return wn
        except Exception:
            pass
    return latest_title or ""


def storyline_deltas(state: dict, limit: int | None) -> list[dict]:
    """Threads that moved since the last send: ``last_updated`` advanced past the
    cursor AND the thread gained sids we have not already mailed. Sorted newest
    first; ``limit`` caps the daily brief (weekly passes None for the full set).
    """
    idx_path = ROOT / "data" / "storylines" / "index.json"
    if not idx_path.exists():
        return []
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    cur = state.get("storylines", {})
    sent_through = cur.get("sent_through") or ""
    seen = set(cur.get("seen_sids") or [])

    out: list[dict] = []
    for s in idx.get("storylines", []):
        last_updated = s.get("last_updated") or ""
        member_sids = s.get("member_sids") or []
        new_sids = [x for x in member_sids if x not in seen]
        if last_updated > sent_through and new_sids:
            out.append(
                {
                    "slug": s.get("slug", ""),
                    "label": s.get("label") or s.get("slug", ""),
                    "last_updated": last_updated,
                    "member_sids": member_sids,
                    "latest_title": s.get("latest_title") or "",
                    "item_count": int(s.get("item_count") or 0),
                    "day_count": int(s.get("day_count") or 0),
                    "whats_new": narrative_copy(s.get("slug", ""), last_updated, s.get("latest_title", "")),
                }
            )
    out.sort(key=lambda r: r["last_updated"], reverse=True)
    return out if limit is None else out[:limit]


def storylines_in_window(start: str, end: str, limit: int | None) -> list[dict]:
    """Weekly recap: threads whose ``last_updated`` falls within the recap week
    ``[start, end]`` (YYYY-MM-DD). Window-based — NOT cursor-based — because the
    daily send advances the shared storyline cursor, which would starve a
    cursor-based weekly. A thread re-appearing in both a daily and the Friday
    roundup is intended: "new today" vs. "what happened this week".
    """
    idx_path = ROOT / "data" / "storylines" / "index.json"
    if not idx_path.exists():
        return []
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[dict] = []
    for s in idx.get("storylines", []):
        last_updated = s.get("last_updated") or ""
        if start <= last_updated[:10] <= end:
            out.append(
                {
                    "slug": s.get("slug", ""),
                    "label": s.get("label") or s.get("slug", ""),
                    "last_updated": last_updated,
                    "latest_title": s.get("latest_title") or "",
                    "item_count": int(s.get("item_count") or 0),
                    "day_count": int(s.get("day_count") or 0),
                    "whats_new": narrative_copy(s.get("slug", ""), last_updated, s.get("latest_title", "")),
                }
            )
    out.sort(key=lambda r: r["last_updated"], reverse=True)
    return out if limit is None else out[:limit]


def wiki_in_window(start: str, end: str, limit: int | None) -> list[dict]:
    """Weekly recap: knowledge-map nodes edited within ``[start, end]`` (node
    ``updated``, YYYY-MM-DD — a real page edit, not the index ``generated_at``
    that every compile bumps). Evergreen, slow-moving content — weekly only, so
    it never dilutes the daily brief's finishability.
    """
    idx_path = ROOT / "data" / "wiki" / "index.json"
    if not idx_path.exists():
        return []
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    nodes = idx.get("nodes") or {}
    out: list[dict] = []
    for node in nodes.values():
        updated = node.get("updated") or ""
        if start <= updated <= end:
            summary = " ".join(str(node.get("summary") or "").split())
            out.append(
                {
                    "slug": node.get("slug", ""),
                    "title": node.get("title", ""),
                    "kind": node.get("kind", ""),
                    "area": node.get("area", ""),
                    "updated": updated,
                    "summary": summary,
                }
            )
    out.sort(key=lambda r: (r["updated"], r["title"]), reverse=True)
    return out if limit is None else out[:limit]


# --------------------------------------------------------------------------- #
# HTML email
# --------------------------------------------------------------------------- #
def unsubscribe_html(cfg: dict, locale: str = "en") -> str:
    """Resend broadcasts template the unsubscribe URL into the body via the
    `{{{RESEND_UNSUBSCRIBE_URL}}}` token (compliance + one-click unsubscribe).
    Returned as a plain string so the triple braces survive f-string footers.
    Buttondown appends its own unsubscribe footer, so it needs nothing here.
    """
    if (cfg.get("provider") or "").lower() == "resend":
        return ' · <a href="{{{RESEND_UNSUBSCRIBE_URL}}}" style="color:#999">' + _t(locale, "unsubscribe") + "</a>"
    return ""


def language_switch_html(cfg: dict, locale: str = "en") -> str:
    """Footer link to the signup page with the other edition preselected.
    Re-subscribing there moves an existing reader to that edition
    (``api/subscribe.js``). Empty until the Korean segment is configured."""
    if not segment_for("ko"):
        return ""
    other = "en" if locale == "ko" else "ko"
    url = f"{cfg['site_base'].rstrip('/')}/subscribe?lang={other}&utm_source={cfg['utm_source']}&utm_content=footer"
    return (
        f' · <a href="{html.escape(url)}" style="color:#999" lang="{other}">'
        f"{html.escape(_t(locale, 'switch_lang'))}</a>"
    )


EMAIL_FONT_STACK = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
EMAIL_FONT_STACK_KO = (
    "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',"
    "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
)


def wrapper_attrs(locale: str = "en") -> str:
    """Attributes for the email's outer container. Korean breaks lines between
    words (keep-all) instead of mid-word, the same rule the web pages use, and
    names Hangul fonts before the Latin fallbacks."""
    style = "max-width:640px;margin:0 auto;padding:24px 18px;color:#111;background:#ffffff;"
    if locale == "ko":
        return (
            f'lang="ko" style="{style}font-family:{EMAIL_FONT_STACK_KO};'
            'word-break:keep-all;overflow-wrap:break-word"'
        )
    return f'style="{style}font-family:{EMAIL_FONT_STACK}"'


EN_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
EN_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
KO_WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")


def header_date(day: str, locale: str = "en") -> str:
    """``2026-11-18`` as the email header shows it: ``Wed, Nov 18`` or
    ``11월 18일 (수)``. Falls back to the raw string when it is not a date."""
    try:
        d = datetime.strptime(str(day)[:10], "%Y-%m-%d")
    except ValueError:
        return str(day)
    if locale == "ko":
        return f"{d.month}월 {d.day}일 ({KO_WEEKDAYS[d.weekday()]})"
    return f"{EN_WEEKDAYS[d.weekday()]}, {EN_MONTHS[d.month - 1]} {d.day}"


def week_range(wk: dict, locale: str = "en") -> str:
    """The week's span for the subject line: ``Nov 7–13`` or ``11월 7–13일``."""
    try:
        a = datetime.strptime(str(wk.get("start"))[:10], "%Y-%m-%d")
        b = datetime.strptime(str(wk.get("end"))[:10], "%Y-%m-%d")
    except ValueError:
        return str(wk.get("week") or "")
    if locale == "ko":
        tail = f"{b.day}일" if a.month == b.month else f"{b.month}월 {b.day}일"
        return f"{a.month}월 {a.day}–{tail}"
    tail = f"{b.day}" if a.month == b.month else f"{EN_MONTHS[b.month - 1]} {b.day}"
    return f"{EN_MONTHS[a.month - 1]} {a.day}–{tail}"


def share_html(cfg: dict, page_url: str, title: str, locale: str = "en") -> str:
    """"Forward it" line: a mailto link that opens a new message with the web
    version and the signup link already filled in."""
    base = cfg["site_base"].rstrip("/")
    sub_url = f"{base}/subscribe{'?lang=ko' if locale == 'ko' else ''}"
    subject = _t(locale, "share_subject", title=title)
    body = _t(locale, "share_body", url=page_url.split("?")[0], sub=sub_url)
    href = f"mailto:?subject={quote(subject)}&body={quote(body)}"
    return (
        '<div style="margin:0 0 14px;text-align:center;font-size:15px">'
        f'<a href="{html.escape(href)}" style="color:#1a6dd6;text-decoration:none;font-weight:600">'
        f"{html.escape(_t(locale, 'share'))}</a></div>"
    )


# Dark mode. Clients that honour prefers-color-scheme (Apple Mail, iOS Mail,
# Outlook for Mac) apply these; the others keep the light design or invert it
# themselves. Every inline colour the template uses maps to one class below
# (``add_dark_classes``), so the template stays plain inline styles.
DARK_CSS = (
    ":root{color-scheme:light dark;supported-color-schemes:light dark}"
    "@media (prefers-color-scheme: dark){"
    ".ld-bg{background:#121417!important}"
    ".ld-card{background:#1c2026!important}"
    ".ld-text{color:#e6edf3!important}"
    ".ld-soft{color:#c9d1d9!important}"
    ".ld-muted{color:#8b949e!important}"
    ".ld-link{color:#6cb6ff!important}"
    ".ld-ok{color:#56d364!important}"
    ".ld-violet{color:#c297ff!important}"
    ".ld-rule{border-color:#30363d!important}"
    "}"
)
_DARK_COLOR_CLASSES = {
    "#111": "ld-text",
    "#333": "ld-soft",
    "#444": "ld-soft",
    "#555": "ld-soft",
    "#666": "ld-muted",
    "#777": "ld-muted",
    "#888": "ld-muted",
    "#999": "ld-muted",
    "#57606a": "ld-muted",
    "#1a6dd6": "ld-link",
    "#1a7f37": "ld-ok",
    "#7a3fb8": "ld-violet",
}
_DARK_BG_CLASSES = {"#f6f8fa": "ld-card", "#ffffff": "ld-bg"}
_STYLED_TAG = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)((?:\s+[a-zA-Z-]+="[^"]*")*?)\s+style="([^"]*)"([^>]*)>')


def add_dark_classes(body: str) -> str:
    """Tag each styled element with the dark-mode class for its colours."""

    def repl(m: re.Match) -> str:
        tag, before, style, after = m.groups()
        classes: list[str] = []
        for prop, value in re.findall(r"(?:^|;)\s*(color|background|background-color)\s*:\s*(#[0-9a-fA-F]{3,6})", style):
            mapping = _DARK_COLOR_CLASSES if prop == "color" else _DARK_BG_CLASSES
            if value.lower() in mapping:
                classes.append(mapping[value.lower()])
        if re.search(r"border(?:-top|-bottom)?\s*:\s*1px solid #(?:eee|f0f0f0|d8dee4)", style):
            classes.append("ld-rule")
        if not classes:
            return m.group(0)
        existing = re.search(r'\sclass="([^"]*)"', before + after)
        if existing:
            merged = " ".join(dict.fromkeys(existing.group(1).split() + classes))
            return m.group(0).replace(existing.group(0), f' class="{merged}"', 1)
        return f'<{tag}{before} style="{style}" class="{" ".join(dict.fromkeys(classes))}"{after}>'

    return _STYLED_TAG.sub(repl, body)


def email_document(inner: str, locale: str = "en") -> str:
    """Wrap a rendered body in a full HTML document that declares light and
    dark support and carries the dark-mode styles."""
    return (
        f'<!DOCTYPE html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="supported-color-schemes" content="light dark">'
        f"<style>{DARK_CSS}</style></head>"
        f'<body style="margin:0;padding:0;background:#ffffff" class="ld-bg">{add_dark_classes(inner)}</body></html>'
    )


def logo_img(cfg: dict) -> str:
    """Small brand mark for the email header (absolute URL — email clients can't
    resolve site-relative paths). Square logo served from the site root."""
    src = f"{cfg['site_base'].rstrip('/')}/logo.png"
    return (
        f'<img src="{html.escape(src)}" alt="" width="22" height="22" '
        f'style="width:22px;height:22px;vertical-align:middle;margin-right:7px;border-radius:5px">'
    )


def html_to_text(body: str) -> str:
    """Derive a plain-text alternative from the rendered HTML body (improves
    deliverability and serves text-only clients). Not a full HTML parser — a
    targeted converter for our own known markup: drops the hidden preheader and
    the one-tap feedback rows (noise in text), renders links as ``text (url)``,
    and turns block elements into line breaks.
    """
    s = re.sub(r"<head>.*?</head>", "", body, count=1, flags=re.S | re.I)
    s = re.sub(r'<div style="display:none.*?</div>', "", s, count=1, flags=re.S)
    s = re.sub(r'<span class="ld-fb">.*?</span>', "", s, flags=re.S)
    s = re.sub(
        r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        lambda m: f"{re.sub('<[^>]+>', '', m.group(2))} ({html.unescape(m.group(1))})",
        s,
        flags=re.S,
    )
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(h1|h2|h3|div|tr|li|p|table|ul)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


HANGUL_RE = re.compile(r"[가-힣]")


def reading_minutes(fragment: str, locale: str = "en") -> int:
    """Minutes to read the brief itself (summary, intro, themes), from the text
    the email actually shows, at about 230 space-separated words a minute
    (English words, Korean eojeol). Feedback links and the footer are left out."""
    text = re.sub(r'<span class="ld-fb">.*?</span>', " ", fragment, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return max(2, round(len(text.split()) / 230))


def render_storyline_rows(cfg: dict, threads: list[dict], locale: str = "en") -> str:
    """Storyline rows for the digest. The link names the thread's newest story
    (the cluster label is a machine keyword, not a headline), the narrative
    says what happened next, and a small meta line gives its size. The
    Korean edition keeps only rows whose narrative is in Korean."""
    rows = []
    for t in threads:
        if locale != "en" and not (t.get("localized") and HANGUL_RE.search(str(t.get("whats_new") or ""))):
            continue
        wn = clean(str(t.get("whats_new") or ""), 220)
        latest = clean(str(t.get("latest_title") or ""), 120)
        if locale == "en":
            head, body = (latest or t.get("label") or ""), (wn if wn and wn != latest else "")
        else:
            head, body = wn, ""
        meta = _t(locale, "storyline_meta", n=int(t.get("item_count") or 0), d=int(t.get("day_count") or 0))
        url = storyline_url(cfg, t["slug"], locale if t.get("localized") else "en") + "&utm_content=storylines"
        rows.append(
            '<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0">'
            f'<div style="font-size:16px;font-weight:600;line-height:1.4"><a href="{html.escape(url)}" '
            f'style="color:#1a6dd6;text-decoration:none">{html.escape(head)} →</a></div>'
            + (f'<div style="font-size:15px;line-height:1.5;color:#444;margin-top:3px">{html.escape(body)}</div>' if body else "")
            + f'<div style="font-size:13px;color:#888;margin-top:3px">{html.escape(meta)}</div></td></tr>'
        )
    return "".join(rows)


def render_daily(cfg: dict, recap: dict, threads: list[dict], locale: str = "en") -> tuple[str, str]:
    """Render the curated daily recap (``data/daily/latest.json``) as the brief.

    Mirrors the ``/daily`` page — the same intro, highlights ("In 30 seconds"),
    and themed categories — so the email and the page show one editorial recap,
    plus the email-only "Continuing threads" storyline deltas, one-tap feedback
    links, and the "you're caught up" end marker. Returns (subject, html_body).
    """
    articles = daily_articles(recap)
    cats = [c for c in (recap.get("categories") or []) if isinstance(c, dict)]
    n = len(articles)
    recap_date = (recap.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
    top_title = clean(articles[0].get("title", "AI updates"), 60) if articles else "AI updates"

    # "In 30 seconds" TL;DR (highlights) then the editorial intro paragraphs —
    # the same lead the /daily page shows above the categories.
    highlights = [clean(h, 200) for h in (recap.get("highlights") or []) if isinstance(h, str) and h.strip()]
    tldr_html = ""
    if highlights:
        lis = "".join(f'<li style="margin:4px 0">{html.escape(h)}</li>' for h in highlights)
        tldr_html = (
            '<div style="margin:6px 0 14px;padding:12px 14px;border-radius:8px;background:#f6f8fa">'
            '<div style="font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;'
            f'color:#1a6dd6;margin-bottom:6px">{_t(locale, "tldr")}</div>'
            f'<ul style="font-size:15px;line-height:1.5;color:#333;padding-left:18px;margin:0">{lis}</ul></div>'
        )
    intro_paras = [clean(p, 500) for p in (recap.get("intro") or []) if isinstance(p, str) and p.strip()]
    intro_html = "".join(
        f'<p style="font-size:16px;line-height:1.6;color:#333;margin:0 0 10px">{html.escape(p)}</p>'
        for p in intro_paras[:2]
    )

    video_html = video_link_html(cfg, recap, site_path(locale, f"/daily/{recap_date}"), _t(locale, "video_daily"))

    # Themed categories: each article links to its /story/<sid> permalink. The
    # first `full_items_per_theme` carry their source and recap summary; the
    # rest are one-line headlines, so the brief stays short enough to finish.
    # The one-tap 👍 / 👎 feedback rides on every item's source line.
    full_per_theme = int((cfg.get("daily") or {}).get("full_items_per_theme", 2))
    cat_html: list[str] = []
    for idx, c in enumerate(cats, 1):
        name = html.escape(clean(c.get("name", ""), 80))
        csum = html.escape(clean(c.get("summary", ""), 220))
        arts: list[str] = []
        raw_articles = [a for a in (c.get("articles") or []) if isinstance(a, dict)]
        for pos, a in enumerate(raw_articles):
            url = a.get("url", "")
            title = html.escape(clean(a.get("title", ""), 140))
            src = html.escape(clean(source_name(a.get("source", "")), 40))
            full = pos < full_per_theme
            link = html.escape(story_url(cfg, url) + ("&utm_content=story" if full else "&utm_content=headline"))
            if full:
                asum = html.escape(clean(a.get("summary", ""), 180))
                arts.append(
                    '<tr><td style="padding:12px 0;border-bottom:1px solid #eee">'
                    f'<div style="font-size:17px;font-weight:600;line-height:1.35">'
                    f'<a href="{link}" style="color:#111;text-decoration:none">{title}</a></div>'
                    + (f'<div style="font-size:15px;line-height:1.5;color:#444;margin-top:4px">{asum}</div>' if asum else "")
                    + f'<div style="font-size:13px;color:#888;margin-top:5px">{src}{feedback_links(cfg, url, locale)}</div>'
                    + "</td></tr>"
                )
                continue
            if pos == full_per_theme:
                arts.append(
                    '<tr><td style="padding:12px 0 2px;font-size:12px;font-weight:700;letter-spacing:.04em;'
                    f'text-transform:uppercase;color:#57606a">{_t(locale, "more_in_theme")}</td></tr>'
                )
            arts.append(
                '<tr><td style="padding:7px 0;border-bottom:1px solid #eee">'
                f'<a href="{link}" style="font-size:16px;font-weight:600;line-height:1.35;color:#111;text-decoration:none">{title}</a>'
                f'<div style="font-size:13px;color:#888;margin-top:2px">{src}{feedback_links(cfg, url, locale, short=True)}</div>'
                "</td></tr>"
            )
        article_count = len(raw_articles)
        item_label = _t(locale, "item") if article_count == 1 else _t(locale, "items")
        cat_html.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:24px 0 2px;border-top:1px solid #d8dee4;background:#f6f8fa">'
            '<tr><td style="padding:10px 12px">'
            f'<div style="font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;'
            f'color:#57606a">{_t(locale, "theme", idx=idx, n=article_count, items=item_label)}</div>'
            f'<div style="font-size:18px;font-weight:700;line-height:1.35;color:#111;margin-top:2px">{name}</div>'
            + (f'<div style="font-size:15px;line-height:1.45;color:#555;margin-top:3px">{csum}</div>' if csum else "")
            + "</td></tr></table>"
            + f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(arts)}</table>'
        )
    cats_html = "".join(cat_html)
    mins = reading_minutes(tldr_html + intro_html + cats_html, locale)
    subject = _t(locale, "daily_subject", n=n, mins=mins, top=top_title)

    thread_html = ""
    rows = render_storyline_rows(cfg, threads, locale)
    if rows:
        thread_html = (
            f'<h2 style="font-size:18px;margin:28px 0 6px">{_t(locale, "threads_daily")}</h2>'
            '<div style="font-size:13px;color:#888;margin-bottom:6px">'
            f'{_t(locale, "threads_daily_dek")}</div>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        )

    feed_url = f"{cfg['site_base'].rstrip('/')}{site_path(locale, '/')}?utm_source={cfg['utm_source']}&utm_content=footer"
    daily_page = f"{cfg['site_base'].rstrip('/')}{site_path(locale, f'/daily/{recap_date}')}?utm_source={cfg['utm_source']}&utm_content=footer"
    weekly_url = f"{cfg['site_base'].rstrip('/')}/weekly?utm_source={cfg['utm_source']}&utm_content=footer"
    unsub = unsubscribe_html(cfg, locale)
    lang_switch = language_switch_html(cfg, locale)
    n_cats = len(cats)
    sub_meta = _t(locale, "daily_meta", n=n, cats=n_cats, s="s" if n_cats != 1 else "", mins=mins)
    preheader = html.escape(_preheader(recap, articles, locale))
    community_html = render_community_email(cfg, "daily", recap_date, locale)
    inner = f"""\
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:#fff">{preheader}{PREHEADER_PAD}</div>
<div {wrapper_attrs(locale)}>
  <div style="font-size:13px;color:#999;letter-spacing:.04em;text-transform:uppercase">{logo_img(cfg)}LLM Digest · {header_date(recap_date, locale)}</div>
  <h1 style="font-size:22px;margin:6px 0 2px">{_t(locale, "daily_h1")}</h1>
  <div style="font-size:15px;color:#777;margin-bottom:12px">{sub_meta}</div>
  {tldr_html}
  {video_html}
  {intro_html}
  {community_html}
  {cats_html}
  {thread_html}
  <div style="margin:26px 0 14px;padding:12px;border-radius:8px;background:#f6f8fa;text-align:center;font-size:16px;font-weight:600;color:#1a7f37">{_t(locale, "caught_up")}</div>
  {share_html(cfg, daily_page, top_title, locale)}
  <div style="font-size:13px;color:#999;margin-top:18px;line-height:1.9">
    <a href="{html.escape(daily_page)}" style="color:#1a6dd6">{_t(locale, "web")}</a> ·
    <a href="{html.escape(feed_url)}" style="color:#1a6dd6">{_t(locale, "feed")}</a> ·
    <a href="{html.escape(weekly_url)}" style="color:#1a6dd6">{_t(locale, "week_link")}</a>{lang_switch}{unsub}
    <div style="margin-top:8px;line-height:1.6">{_t(locale, "why")} {_t(locale, "tagline")}</div>
  </div>
</div>"""
    inner = with_utm(cfg, inner, utm_medium="email", utm_campaign=f"daily-{recap_date}-{locale}")
    return subject, email_document(inner, locale)


def render_community_email(cfg: dict, kind: str, edition: str, locale: str = "en") -> str:
    """The "From the community" block: the recap's agent-written thread, or ""
    when there is no valid post or no thread in ``locale`` for this edition."""
    if not edition:
        return ""
    post = community.load_post(kind, edition)
    thread = community.thread_for(post, locale)
    if not thread:
        return ""
    base = cfg["site_base"].rstrip("/")
    url = f"{base}{community.post_path(kind, edition, locale)}?utm_source={cfg['utm_source']}&utm_content=community"
    title = html.escape(clean(str(thread.get("title") or ""), 160))
    n = community.comment_count(thread.get("comments"))
    top = community.top_comment(thread)
    quote_html = ""
    if top:
        first = (community.lines(top.get("body")) or [""])[0]
        quote_html = (
            '<div style="font-size:15px;line-height:1.5;color:#444;margin-top:6px">'
            f'<strong style="color:#111">{html.escape(clean(str(top.get("author") or ""), 40))}</strong> '
            f"{html.escape(clean(first, 200))}</div>"
        )
    period = _t(locale, "period_daily" if kind == "daily" else "period_weekly")
    return (
        '<div style="margin:18px 0 22px;padding:12px 14px;border-radius:8px;border-left:4px solid #1a6dd6;background:#f6f8fa">'
        '<div style="font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:#1a6dd6">'
        f"{_t(locale, 'community')}</div>"
        f'<div style="font-size:17px;font-weight:600;line-height:1.35;margin-top:4px">'
        f'<a href="{html.escape(url)}" style="color:#111;text-decoration:none">{title}</a></div>'
        f'<div style="font-size:13px;color:#888;margin-top:3px">{html.escape(_t(locale, "community_meta", period=period, n=n))}</div>'
        f"{quote_html}"
        f'<div style="font-size:15px;font-weight:600;margin-top:8px"><a href="{html.escape(url)}" '
        f'style="color:#1a6dd6;text-decoration:none">{_t(locale, "read_thread")}</a></div></div>'
    )


def render_skill_lab_email(cfg: dict, lab: dict | None) -> str:
    """Render one bounded weekly Skill Lab promotion, or nothing."""
    if not isinstance(lab, dict):
        return ""
    slug = str(lab.get("slug") or "")
    state = str(lab.get("state") or "")
    edition = lab.get("pilot_edition")
    size = lab.get("pilot_size")
    if not SKILL_LAB_SLUG_RE.match(slug) or state not in {"protocol", "published"}:
        return ""
    if not isinstance(edition, int) or not isinstance(size, int):
        return ""
    base = cfg["site_base"].rstrip("/")
    source = quote(str(cfg.get("utm_source") or "email"), safe="")
    detail_url = (
        f"{base}/playbook/lab/{slug}?utm_source={source}"
        f"&utm_medium=email&utm_campaign=skill_lab_{edition}&ref=weekly_email"
    )
    status = "60-second verdict" if state == "published" else "Protocol, no results yet"
    lead = lab.get("verdict") if state == "published" else lab.get("summary")
    cta = "See the evidence" if state == "published" else "Read the protocol"
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:26px 0 4px;border-top:1px solid #d8dee4;border-bottom:1px solid #d8dee4">'
        '<tr><td style="padding:14px 12px;border-left:3px solid #2457d6;background:#f6f8fa">'
        f'<div style="font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#2457d6">'
        f'Agent Skill Lab · Pilot {edition}/{size}</div>'
        f'<div style="font-size:17px;font-weight:700;line-height:1.3;color:#111;margin-top:4px">'
        f'{html.escape(clean(str(lab.get("title") or "Agent Skill Lab"), 120))}</div>'
        f'<div style="font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:#23875b;margin-top:8px">'
        f'{html.escape(status)}</div>'
        f'<div style="font-size:15px;line-height:1.5;color:#444;margin-top:3px">'
        f'{html.escape(clean(str(lead or ""), 240))}</div>'
        f'<div style="margin-top:10px"><a href="{html.escape(detail_url)}" '
        f'style="color:#2457d6;font-size:15px;font-weight:700;text-decoration:none">{cta} →</a></div>'
        '</td></tr></table>'
    )


def render_weekly(
    cfg: dict,
    wk: dict,
    threads: list[dict],
    wiki: list[dict],
    skill_lab: dict | None = None,
    locale: str = "en",
) -> tuple[str, str]:
    """Returns (subject, html_body) for the weekly recap in ``locale``."""
    title = wk.get("title") or f"What happened in AI — week {wk.get('week','')}"
    lead = next((h for h in (wk.get("highlights") or []) if isinstance(h, str) and h.strip()), "")
    subject = (
        _t(locale, "weekly_subject", top=clean(lead.rstrip(". "), 70), range=week_range(wk, locale))
        if lead
        else title
    )
    base = cfg["site_base"].rstrip("/")
    utm = cfg["utm_source"]

    intro = wk.get("intro") or []
    intro_html = "".join(
        f'<p style="font-size:16px;line-height:1.6;color:#333;margin:0 0 10px">{html.escape(p)}</p>'
        for p in intro[:2]
    )

    highlights = wk.get("highlights") or []
    hl_html = ""
    if highlights:
        lis = "".join(f'<li style="margin:4px 0">{html.escape(h)}</li>' for h in highlights)
        hl_html = (
            f'<h2 style="font-size:18px;margin:22px 0 6px">{_t(locale, "weekly_highlights")}</h2>'
            f'<ul style="font-size:16px;line-height:1.5;color:#333;padding-left:20px;margin:0">{lis}</ul>'
        )

    fav = reader_favorites(int(cfg["weekly"].get("max_favorites", 3)))
    fav_html = ""
    if fav:
        chips = " · ".join(
            f'<span style="color:#333;font-weight:600">{html.escape(source_name(s))}</span>' for s, _ in fav
        )
        fav_html = (
            '<div style="margin:18px 0 4px;padding:10px 12px;border-radius:8px;background:#f6f8fa;font-size:15px;color:#555">'
            f"{_t(locale, 'favorites', chips=chips)}</div>"
        )

    per_cat = int(cfg["weekly"]["articles_per_category"])
    cat_html = []
    for c in wk.get("categories") or []:
        arts = []
        for a in (c.get("articles") or [])[:per_cat]:
            url = a.get("url", "")
            t = html.escape(clean(a.get("title", ""), 130))
            src = html.escape(clean(source_name(a.get("source", "")), 32))
            arts.append(
                f'<li style="margin:5px 0;font-size:15px;line-height:1.4">'
                f'<a href="{html.escape(story_url(cfg, url) + "&utm_content=story")}" style="color:#111;text-decoration:none">{t}</a>'
                f' <span style="color:#999">· {src}</span></li>'
            )
        cat_html.append(
            f'<div style="margin:14px 0"><div style="font-size:17px;font-weight:600">{html.escape(c.get("name",""))}</div>'
            f'<div style="font-size:15px;color:#666;margin:2px 0 4px">{html.escape(clean(c.get("summary",""), 220))}</div>'
            f'<ul style="padding-left:18px;margin:0;list-style:disc">{"".join(arts)}</ul></div>'
        )
    cats_section = (
        f'<h2 style="font-size:18px;margin:24px 0 4px">{_t(locale, "by_theme")}</h2>' + "".join(cat_html) if cat_html else ""
    )

    thread_html = ""
    rows = render_storyline_rows(cfg, threads, locale)
    if rows:
        thread_html = (
            f'<h2 style="font-size:18px;margin:26px 0 6px">{_t(locale, "threads_weekly")}</h2>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        )

    wiki_html = ""
    if wiki:
        wr = []
        for w in wiki:
            topic_url = f"{base}{site_path(locale if w.get('localized') else 'en', '/topic/' + str(w['slug']))}?utm_source={utm}&utm_content=wiki"
            kind = _t(locale, "obstacle") if w["kind"] == "obstacle" else _t(locale, "solution")
            wr.append(
                f'<tr><td style="padding:9px 0;border-bottom:1px solid #f0f0f0">'
                f'<div style="font-size:16px;font-weight:600"><a href="{html.escape(topic_url)}" '
                f'style="color:#7a3fb8;text-decoration:none">{html.escape(clean(w["title"], 120))} →</a>'
                f'<span style="font-size:12px;color:#999;font-weight:400"> · {kind}</span></div>'
                f'<div style="font-size:15px;color:#444;margin-top:3px">{html.escape(clean(w["summary"], 200))}</div></td></tr>'
            )
        wiki_html = (
            f'<h2 style="font-size:18px;margin:26px 0 6px">{_t(locale, "wiki")}</h2>'
            '<div style="font-size:13px;color:#888;margin-bottom:6px">'
            f'{_t(locale, "wiki_dek")}</div>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(wr)}</table>'
        )

    feed_url = f"{base}{site_path(locale, '/')}?utm_source={utm}&utm_content=footer"
    weekly_page = f"{base}{site_path(locale, '/weekly/' + str(wk.get('week', '')))}?utm_source={utm}&utm_content=footer"
    unsub = unsubscribe_html(cfg, locale)
    lang_switch = language_switch_html(cfg, locale)
    pre = clean(highlights[0], 110) if highlights else clean(" ".join(intro[:1]), 110)
    preheader = html.escape(f"{pre}{_t(locale, 'weekly_preheader_tail')}")
    skill_lab_html = render_skill_lab_email(cfg, skill_lab)
    community_html = render_community_email(cfg, "weekly", str(wk.get("week") or ""), locale)
    video_html = video_link_html(cfg, wk, site_path(locale, f"/weekly/{wk.get('week','')}"), _t(locale, "video_weekly"))
    inner = f"""\
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:#fff">{preheader}{PREHEADER_PAD}</div>
<div {wrapper_attrs(locale)}>
  <div style="font-size:13px;color:#999;letter-spacing:.04em;text-transform:uppercase">{logo_img(cfg)}{_t(locale, "weekly_header")}</div>
  <h1 style="font-size:23px;margin:6px 0 10px">{html.escape(title)}</h1>
  {video_html}
  {intro_html}
  {hl_html}
  {community_html}
  {fav_html}
  {cats_section}
  {thread_html}
  {wiki_html}
  {skill_lab_html}
  <div style="margin-top:24px">{share_html(cfg, weekly_page, title, locale)}</div>
  <div style="font-size:13px;color:#999;margin-top:18px;line-height:1.9">
    <a href="{html.escape(weekly_page)}" style="color:#1a6dd6">{_t(locale, "full_recap")}</a> ·
    <a href="{html.escape(feed_url)}" style="color:#1a6dd6">{_t(locale, "open_feed")}</a>{lang_switch}{unsub}
    <div style="margin-top:8px;line-height:1.6">{_t(locale, "why")} {_t(locale, "tagline")}</div>
  </div>
</div>"""
    inner = with_utm(cfg, inner, utm_medium="email", utm_campaign=f"weekly-{wk.get('week', '')}-{locale}")
    return subject, email_document(inner, locale)


# --------------------------------------------------------------------------- #
# Provider send (broadcast)
# --------------------------------------------------------------------------- #
def segment_for(locale: str) -> str:
    """The Resend segment a locale's broadcast targets ("" when unset)."""
    if locale == "ko":
        return (os.getenv("EMAIL_SEGMENT_ID_KO") or "").strip()
    return (os.getenv("EMAIL_SEGMENT_ID") or os.getenv("EMAIL_AUDIENCE_ID") or "").strip()


def resolve_topic_id(kind: str) -> str:
    """The Resend Topic a given digest kind scopes to. Daily and weekly are
    separate topics so a reader can take "weekly only — less email" (opted out
    of the daily topic but kept in the weekly one); the per-topic preference is
    set at signup (see ``api/subscribe.js``) and Resend's hosted preference page
    manages it thereafter. Falls back to the legacy single ``EMAIL_TOPIC_ID``
    (both digests, one topic) when the per-kind ids aren't configured."""
    per_kind = {
        "daily": os.getenv("EMAIL_TOPIC_ID_DAILY"),
        "weekly": os.getenv("EMAIL_TOPIC_ID_WEEKLY"),
    }.get(kind)
    return (per_kind or os.getenv("EMAIL_TOPIC_ID") or "").strip()


def send_broadcast(
    cfg: dict,
    api_key: str,
    subject: str,
    html_body: str,
    name: str = "",
    kind: str = "daily",
    locale: str = "en",
) -> bool:
    """Send the broadcast. Returns True if sent, False for a clean no-op
    (e.g. the recipient segment is empty — nothing to send, not an error).

    ``name`` is the provider-side internal label shown in the dashboard
    broadcast list (distinct from the subscriber-facing ``subject``). Without
    it Resend lists every broadcast as "Untitled". ``kind`` selects the Resend
    Topic the send scopes to (daily vs weekly), so per-digest opt-outs hold.
    ``locale`` selects the recipient segment: English readers are in
    ``EMAIL_SEGMENT_ID``, Korean readers in ``EMAIL_SEGMENT_ID_KO``."""
    provider = (cfg.get("provider") or "buttondown").lower()
    text_body = html_to_text(html_body)
    if provider == "buttondown":
        if locale != "en":
            print(f"email_send_skipped=true locale={locale} reason=buttondown_single_list")
            return False
        r = requests.post(
            "https://api.buttondown.com/v1/emails",
            headers={"Authorization": f"Token {api_key}"},
            json={"subject": subject, "body": html_body, "email_type": "public"},
            timeout=30,
        )
        r.raise_for_status()
        return True
    elif provider == "resend":
        # Audiences were renamed to Segments; a broadcast targets a segment_id
        # (optionally scoped to a topic_id). `send: true` creates + sends in one
        # call. The unsubscribe link is templated into the body (see footers).
        segment_id = segment_for(locale)
        from_addr = os.getenv("EMAIL_FROM", "").strip()
        if not segment_id or not from_addr:
            raise RuntimeError(f"resend requires the {locale} segment id and EMAIL_FROM")
        payload = {
            "segment_id": segment_id,
            "from": from_addr,
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "send": True,
        }
        if name:
            payload["name"] = name
        topic_id = resolve_topic_id(kind)
        if topic_id:
            payload["topic_id"] = topic_id
        r = requests.post(
            "https://api.resend.com/broadcasts",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        # An empty recipient segment is "nothing to send", not a failure: Resend
        # returns 422 "...has no contacts". No-op cleanly instead of crashing the
        # job, the same way we no-op when secrets are absent.
        if r.status_code == 422:
            try:
                msg = (r.json().get("message") or "").lower()
            except Exception:
                msg = r.text.lower()
            if "no contacts" in msg:
                print("email_send_skipped=true reason=empty_segment provider=resend")
                return False
        r.raise_for_status()
        return True
    else:
        raise RuntimeError(f"unknown email provider: {provider}")


def test_body(cfg: dict, html_body: str) -> str:
    """A broadcast body made safe for a one-off test email: Resend fills
    ``{{{...}}}`` tokens only in broadcasts, so the unsubscribe token points at
    the signup page and any other token is dropped."""
    body = html_body.replace("{{{RESEND_UNSUBSCRIBE_URL}}}", f"{cfg['site_base'].rstrip('/')}/subscribe")
    return re.sub(r"\{\{\{[^}]*\}\}\}", "", body)


def send_test(cfg: dict, api_key: str, to: str, subject: str, html_body: str, kind: str, locale: str) -> None:
    """Send one edition to a single address as a normal (non-broadcast)
    Resend email. Never touches a segment, a topic, or the send cursor."""
    if (cfg.get("provider") or "").lower() != "resend":
        raise RuntimeError("test sends need provider: resend")
    from_addr = os.getenv("EMAIL_FROM", "").strip()
    if not from_addr:
        raise RuntimeError("test sends need EMAIL_FROM")
    body = test_body(cfg, html_body)
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": from_addr,
            "to": [to],
            "subject": f"[TEST {kind} {locale}] {subject}",
            "html": body,
            "text": html_to_text(body),
        },
        timeout=30,
    )
    r.raise_for_status()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _latest_daily() -> dict | None:
    """The most recent committed daily recap — ``data/daily/latest.json``, the
    same file the ``/daily`` page serves. None when no recap exists yet (the
    email then no-ops cleanly rather than falling back to the raw feed)."""
    p = ROOT / "data" / "daily" / "latest.json"
    if not p.exists():
        return None
    try:
        recap = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return recap if isinstance(recap, dict) and recap.get("categories") else None


def localized_or_english(kind: str, recap: dict, ident: str, locale: str) -> tuple[dict, str]:
    """The recap to render for ``locale`` and the locale it is actually in.

    A Korean send uses the agent-written translation when it is fresh for the
    English recap; otherwise it falls back to the English email."""
    if locale == "en":
        return recap, "en"
    localized = recap_i18n.load_localized(kind, ident, locale)
    if localized is None:
        print(f"email_locale_fallback=en locale={locale} kind={kind} id={ident} reason=no_fresh_translation")
        return recap, "en"
    return localized, locale


def build_daily(cfg: dict, state: dict, locale: str = "en") -> tuple[str, str, list[dict], str] | None:
    """Returns (subject, body, threads, recap_date), or None when there is no
    daily recap to send (clean no-op)."""
    recap = _latest_daily()
    if not recap:
        return None
    recap_date = (recap.get("date") or "").strip()
    threads = storyline_deltas(state, int(cfg["daily"]["max_threads"]))
    source, used = localized_or_english("daily", recap, recap_date, locale)
    subject, body = render_daily(cfg, source, localize_threads(threads, used), used)
    return subject, body, threads, recap_date


def _latest_weekly() -> dict | None:
    idx_path = ROOT / "data" / "weekly" / "index.json"
    if not idx_path.exists():
        return None
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    rows = [r for r in (idx if isinstance(idx, list) else []) if r.get("end")]
    if not rows:
        return None
    top = max(rows, key=lambda r: r.get("end", ""))
    wk_path = ROOT / "data" / "weekly" / (top.get("path") or f"{top.get('week','')}.json")
    if not wk_path.exists():
        return None
    try:
        return json.loads(wk_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _skill_lab_date(value: object) -> date | None:
    raw = str(value or "")
    if not SKILL_LAB_DATE_RE.match(raw):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _valid_skill_lab_summary(row: object) -> bool:
    return (
        isinstance(row, dict)
        and row.get("schema_version") == 1
        and SKILL_LAB_ID_RE.match(str(row.get("id") or "")) is not None
        and SKILL_LAB_SLUG_RE.match(str(row.get("slug") or "")) is not None
        and isinstance(row.get("pilot_edition"), int)
        and not isinstance(row.get("pilot_edition"), bool)
        and 0 <= row["pilot_edition"] <= 3
        and row.get("pilot_size") == 3
        and row.get("state") in {"protocol", "published"}
        and _skill_lab_date(row.get("date")) is not None
        and _skill_lab_date(row.get("featured_until")) is not None
        and SKILL_LAB_SHA256_RE.match(str(row.get("content_sha256") or "")) is not None
        and row.get("url") == f"/playbook/lab/{row.get('slug')}"
    )


def _sent_skill_lab_ids(state: dict | None) -> set[str]:
    weekly = state.get("weekly", {}) if isinstance(state, dict) else {}
    raw_ids = weekly.get("sent_skill_lab_ids", []) if isinstance(weekly, dict) else []
    if not isinstance(raw_ids, list):
        return set()
    return {
        item
        for item in raw_ids
        if isinstance(item, str) and SKILL_LAB_ID_RE.match(item)
    }


def advance_weekly_state(state: dict, week_key: str, skill_lab_id: str = "") -> None:
    """Advance weekly idempotency and the small, PII-free Lab send cursor."""
    weekly = state.get("weekly", {})
    weekly = dict(weekly) if isinstance(weekly, dict) else {}
    raw_ids = weekly.get("sent_skill_lab_ids", [])
    sent_ids: list[str] = []
    if isinstance(raw_ids, list):
        for item in raw_ids:
            if (
                isinstance(item, str)
                and SKILL_LAB_ID_RE.match(item)
                and item not in sent_ids
            ):
                sent_ids.append(item)
    if SKILL_LAB_ID_RE.match(skill_lab_id) and skill_lab_id not in sent_ids:
        sent_ids.append(skill_lab_id)
    weekly["last_sent_week"] = week_key
    weekly["sent_skill_lab_ids"] = sent_ids[-4:]
    state["weekly"] = weekly


def skill_lab_in_window(
    start: str,
    end: str,
    sent_ids: set[str] | None = None,
) -> dict | None:
    """Return the newest unsent Lab record eligible for this weekly send."""
    start_date = _skill_lab_date(start)
    end_date = _skill_lab_date(end)
    if start_date is None or end_date is None or start_date > end_date:
        return None
    try:
        index = validate_skill_lab_store(SKILL_LAB_DIR, check=True)
    except Exception:
        return None
    if not isinstance(index, list) or len(index) > 4 or not all(
        _valid_skill_lab_summary(row) for row in index
    ):
        return None
    sent_ids = sent_ids or set()
    candidates = [
        row
        for row in index
        if _skill_lab_date(row["date"]) <= end_date
        and _skill_lab_date(row["featured_until"]) >= end_date
        and row["id"] not in sent_ids
    ]
    candidates.sort(
        key=lambda row: (row["pilot_edition"], row["date"]),
        reverse=True,
    )
    for row in candidates:
        slug = str(row["slug"])
        try:
            source = (SKILL_LAB_DIR / f"{slug}.json").read_bytes()
            if hashlib.sha256(source).hexdigest() != row["content_sha256"]:
                return None
            record = json.loads(source)
        except Exception:
            return None
        if (
            isinstance(record, dict)
            and all(record.get(field) == row.get(field) for field in SKILL_LAB_SUMMARY_FIELDS)
            and not validate_skill_lab_record(record)
        ):
            return record
        return None
    return None


def build_weekly(
    cfg: dict,
    state: dict | None = None,
    locale: str = "en",
) -> tuple[str, str, dict, int, int, int, str]:
    wk = _latest_weekly()
    if not wk:
        raise RuntimeError("no weekly recap to render")
    start, end = wk.get("start", ""), wk.get("end", "")
    threads = storylines_in_window(start, end, int(cfg["weekly"]["max_threads"]))
    wiki = wiki_in_window(start, end, int(cfg["weekly"]["max_wiki"]))
    skill_lab = skill_lab_in_window(start, end, _sent_skill_lab_ids(state))
    source, used = localized_or_english("weekly", wk, str(wk.get("week") or ""), locale)
    subject, body = render_weekly(
        cfg, source, localize_threads(threads, used), localize_wiki(wiki, used), skill_lab, used
    )
    skill_lab_id = str(skill_lab.get("id") or "") if skill_lab else ""
    return subject, body, wk, len(threads), len(wiki), int(skill_lab is not None), skill_lab_id


def main() -> int:
    ap = argparse.ArgumentParser(description="Send the email digest")
    ap.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    ap.add_argument(
        "--locale",
        choices=["all", *LOCALES],
        default="all",
        help="language edition(s) to build and send; all = English then Korean",
    )
    ap.add_argument("--dry-run", action="store_true", help="render to stdout, never send, never touch state")
    ap.add_argument("--force", action="store_true", help="ignore the already-sent guard")
    ap.add_argument(
        "--test",
        action="store_true",
        help="send each edition only to EMAIL_TEST_TO, ignore the already-sent guard, never touch state",
    )
    args = ap.parse_args()

    cfg = load_config()
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    locales = list(LOCALES) if args.locale == "all" else [args.locale]

    # Build every edition before sending anything, so each one reads the same
    # cursor state (the English send advances the storyline cursor).
    builds: list[dict] = []
    for locale in locales:
        suffix = "" if locale == "en" else f" [{locale}]"
        state_key = args.kind if locale == "en" else f"{args.kind}_{locale}"
        if args.kind == "weekly":
            build_state = {} if args.force else state
            subject, body, wk, n_threads, n_wiki, n_skill_lab, skill_lab_id = build_weekly(
                cfg, build_state, locale
            )
            week_key = wk.get("week", "")
            builds.append(
                {
                    "locale": locale,
                    "subject": subject,
                    "body": body,
                    "already_sent": state.get(state_key, {}).get("last_sent_week") == week_key,
                    "guard_reason": "already_sent_week",
                    "summary": f"week={week_key} threads={n_threads} wiki={n_wiki} skill_lab={n_skill_lab}",
                    "name": f"Weekly recap — {week_key or today}{suffix}",
                    "week_key": week_key,
                    "skill_lab_id": skill_lab_id,
                    "state_key": state_key,
                }
            )
        else:
            built = build_daily(cfg, state, locale)
            if built is None:
                # No curated recap committed yet — no-op cleanly (never the raw feed).
                print("email_send_skipped=true kind=daily reason=no_recap")
                return 0
            subject, body, threads, recap_date = built
            # Guard on the recap's own date, not the calendar day: send the latest
            # recap once, re-send only when a newer recap appears.
            builds.append(
                {
                    "locale": locale,
                    "subject": subject,
                    "body": body,
                    "already_sent": state.get(state_key, {}).get("last_sent_date") == recap_date,
                    "guard_reason": "already_sent_recap",
                    "summary": f"recap_date={recap_date} threads={len(threads)}",
                    "name": f"Daily brief — {recap_date or today}{suffix}",
                    "threads": threads,
                    "recap_date": recap_date,
                    "state_key": state_key,
                }
            )

    if args.dry_run:
        for b in builds:
            print(f"<!-- locale: {b['locale']} subject: {b['subject']} -->")
            print(b["body"])
            print(f"\n<!-- kind={args.kind} locale={b['locale']} {b['summary']} -->")
        return 0

    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    enabled = bool(cfg.get("enabled")) and bool(api_key)
    if not enabled:
        # Secrets-gated no-op, like PostHog when unconfigured.
        print("email_send_skipped=true reason=disabled_or_no_api_key")
        return 0

    if args.test:
        to = os.getenv("EMAIL_TEST_TO", "").strip()
        if not to:
            print("email_test_failed=true reason=no_EMAIL_TEST_TO")
            return 1
        failed = False
        for b in builds:
            try:
                send_test(cfg, api_key, to, b["subject"], b["body"], args.kind, b["locale"])
            except Exception as exc:
                failed = True
                print(f"email_test_failed=true kind={args.kind} locale={b['locale']} error={str(exc)[:200]}")
                continue
            print(f"email_test_sent=true kind={args.kind} locale={b['locale']} {b['summary']}")
        return 1 if failed else 0

    provider = (cfg.get("provider") or "").lower()
    reader_links = None
    failed = False
    for b in builds:
        locale = b["locale"]
        if b["already_sent"] and not args.force:
            print(f"email_skipped=true kind={args.kind} locale={locale} reason={b['guard_reason']}")
            continue
        if provider == "resend" and not segment_for(locale):
            print(f"email_send_skipped=true kind={args.kind} locale={locale} reason=no_segment")
            continue
        if reader_links is None:
            reader_links = (
                provider == "resend"
                and bool(cfg.get("reader_id_links", True))
                and ensure_reader_id_property(api_key)
            )
            print(f"email_reader_links={'on' if reader_links else 'off'}")
        body = tag_reader_links(cfg, b["body"]) if reader_links else b["body"]
        try:
            sent = send_broadcast(cfg, api_key, b["subject"], body, b["name"], kind=args.kind, locale=locale)
        except Exception as exc:  # one edition failing must not block the others
            failed = True
            print(f"email_send_failed=true kind={args.kind} locale={locale} error={str(exc)[:200]}")
            continue
        if not sent:
            # Nothing was sent (e.g. empty recipient segment). Leave the cursor
            # untouched so the next run re-attempts once contacts exist.
            print(f"email_send_skipped=true kind={args.kind} locale={locale} reason=nothing_sent")
            continue

        # Advance the cursor only after a successful send, so a failure re-sends
        # rather than silently dropping a period. Save after each edition so a
        # later failure never re-sends one that already went out.
        if args.kind == "weekly":
            if locale == "en":
                advance_weekly_state(state, b["week_key"], b["skill_lab_id"])
            else:
                state[b["state_key"]] = {"last_sent_week": b["week_key"]}
        else:
            if locale == "en":
                new_seen = set(state.get("storylines", {}).get("seen_sids") or [])
                newest = state.get("storylines", {}).get("sent_through") or ""
                for t in b["threads"]:
                    new_seen.update(t["member_sids"])
                    if t["last_updated"] > newest:
                        newest = t["last_updated"]
                state["daily"] = {"last_sent_date": b["recap_date"]}
                state["storylines"] = {"sent_through": newest, "seen_sids": sorted(new_seen)}
            else:
                state[b["state_key"]] = {"last_sent_date": b["recap_date"]}
        save_state(state)
        print(f"email_sent=true kind={args.kind} locale={locale} {b['summary']}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
