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
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.story_store import story_sid  # noqa: E402

STATE_PATH = ROOT / "data" / "email" / "state.json"
DEFAULTS = {
    "enabled": False,
    "provider": "buttondown",
    "from_name": "LLM Digest",
    "site_base": "https://www.llm-digest.com",
    "utm_source": "email",
    "daily": {"max_items": 12, "max_threads": 3},
    "weekly": {"max_threads": 12, "articles_per_category": 3, "max_wiki": 4, "max_favorites": 3},
}

# Invisible filler appended after the preheader so the body's first visible line
# doesn't bleed into the inbox preview after the snippet (the standard hack:
# zero-width joiners + non-breaking spaces, which render as nothing).
PREHEADER_PAD = "&#847;&zwnj;&nbsp;" * 40


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
SOURCE_NAMES = {
    "arxiv_cs_ai": "arXiv cs.AI",
    "arxiv_cs_lg": "arXiv cs.LG",
    "arxiv_cs_cl": "arXiv cs.CL",
    "paperswithcode_latest": "Papers with Code",
    "openai_blog": "OpenAI Blog",
    "anthropic_newsroom": "Anthropic Newsroom",
    "anthropic_engineering": "Anthropic Engineering",
    "anthropic_research": "Anthropic Research",
    "huggingface_blog": "Hugging Face Blog",
    "nvidia_blog": "NVIDIA Blog",
    "google_ai_blog": "Google AI Blog",
    "aws_ml_blog": "AWS ML Blog",
    "vllm_releases": "vLLM Releases",
    "triton_releases": "Triton Releases",
    "llamaindex_releases": "LlamaIndex Releases",
    "langgraph_releases": "LangGraph Releases",
    "openai_codex_releases": "OpenAI Codex Releases",
    "claude_code_releases": "Claude Code Releases",
    "claude_agent_sdk_python_releases": "Claude Agent SDK Releases",
    "claude_blog": "Claude Blog",
    "hackernews_ai": "Hacker News AI",
    "infoq_ai_ml": "InfoQ AI/ML",
    "simon_willison": "Simon Willison",
    "latent_space": "Latent Space",
    "langchain_blog": "LangChain Blog",
    "search_agent_engineering_news": "Agent Engineering News",
    "search_llm_ops_news": "LLM Ops News",
}
SOURCE_ACRONYMS = {"ai", "ml", "llm", "aws", "api", "sdk", "gpu"}


def source_name(slug: str) -> str:
    s = (slug or "").strip()
    if not s:
        return "unknown"
    if s in SOURCE_NAMES:
        return SOURCE_NAMES[s]
    return " ".join(
        w.upper() if w.lower() in SOURCE_ACRONYMS else w[:1].upper() + w[1:]
        for w in re.split(r"[_\s]+", s)
        if w
    )


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


def storyline_url(cfg: dict, slug: str) -> str:
    return f"{cfg['site_base'].rstrip('/')}/storyline/{slug}?utm_source={cfg['utm_source']}"


def feedback_url(cfg: dict, url: str, signal: str) -> str:
    """One-tap feedback deep link: lands on the feed with the item highlighted
    and ``?fb=<signal>``, which the client records as the same ``item_feedback``
    event the on-page buttons fire (synced into the auto-tune loop). No new
    endpoint — it reuses the existing share-landing ``?item=<url>`` path.
    """
    base = cfg["site_base"].rstrip("/")
    return f"{base}/?item={quote(url, safe='')}&fb={signal}&utm_source={cfg['utm_source']}"


def feedback_row(cfg: dict, url: str) -> str:
    """Compact 👍 / 👎 line under a daily item."""
    if not url:
        return ""
    useful = html.escape(feedback_url(cfg, url, "useful"))
    irrel = html.escape(feedback_url(cfg, url, "irrelevant"))
    return (
        '<div style="font-size:12px;margin-top:5px">'
        f'<a href="{useful}" style="color:#1a7f37;text-decoration:none">👍 Useful</a>'
        '<span style="color:#ccc"> · </span>'
        f'<a href="{irrel}" style="color:#999;text-decoration:none">👎 Not relevant</a>'
        "</div>"
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


def _preheader(recap: dict, articles: list[dict]) -> str:
    """Inbox-preview snippet: lead with the recap's first highlight (its editorial
    "in 30 seconds"), else the top headlines + remaining count — so the brief
    sells itself in the inbox instead of leaking the boilerplate header.
    """
    highlights = [clean(h, 90) for h in (recap.get("highlights") or []) if isinstance(h, str) and h.strip()]
    if highlights:
        return f"{highlights[0]} — then you're caught up."
    titles = [clean(a.get("title", ""), 50) for a in articles[:2] if a.get("title")]
    extra = max(0, len(articles) - len(titles))
    tail = f" · +{extra} more" if extra else ""
    return f"{' · '.join(titles)}{tail} — then you're caught up."


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
def unsubscribe_html(cfg: dict) -> str:
    """Resend broadcasts template the unsubscribe URL into the body via the
    `{{{RESEND_UNSUBSCRIBE_URL}}}` token (compliance + one-click unsubscribe).
    Returned as a plain string so the triple braces survive f-string footers.
    Buttondown appends its own unsubscribe footer, so it needs nothing here.
    """
    if (cfg.get("provider") or "").lower() == "resend":
        return ' · <a href="{{{RESEND_UNSUBSCRIBE_URL}}}" style="color:#999">Unsubscribe</a>'
    return ""


def logo_img(cfg: dict) -> str:
    """Small brand mark for the email header (absolute URL — email clients can't
    resolve site-relative paths). Square logo served from the site root."""
    src = f"{cfg['site_base'].rstrip('/')}/logo.png"
    return (
        f'<img src="{html.escape(src)}" alt="LLM Digest" width="22" height="22" '
        f'style="width:22px;height:22px;vertical-align:middle;margin-right:7px;border-radius:5px">'
    )


def html_to_text(body: str) -> str:
    """Derive a plain-text alternative from the rendered HTML body (improves
    deliverability and serves text-only clients). Not a full HTML parser — a
    targeted converter for our own known markup: drops the hidden preheader and
    the one-tap feedback rows (noise in text), renders links as ``text (url)``,
    and turns block elements into line breaks.
    """
    s = re.sub(r'<div style="display:none.*?</div>', "", body, count=1, flags=re.S)
    s = re.sub(r'<div style="font-size:12px;margin-top:5px">.*?</div>', "", s, flags=re.S)
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


def render_daily(cfg: dict, recap: dict, threads: list[dict]) -> tuple[str, str]:
    """Render the curated daily recap (``data/daily/latest.json``) as the brief.

    Mirrors the ``/daily`` page — the same intro, highlights ("In 30 seconds"),
    and themed categories — so the email and the page show one editorial recap,
    plus the email-only "Continuing threads" storyline deltas, one-tap feedback
    links, and the "you're caught up" end marker. Returns (subject, html_body).
    """
    articles = daily_articles(recap)
    cats = [c for c in (recap.get("categories") or []) if isinstance(c, dict)]
    n = len(articles)
    mins = max(3, round(n * 0.5))
    recap_date = (recap.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
    top_title = clean(articles[0].get("title", "AI updates"), 60) if articles else "AI updates"
    subject = f"Your AI brief — {n} picks · ~{mins} min · {top_title}"

    # "In 30 seconds" TL;DR (highlights) then the editorial intro paragraphs —
    # the same lead the /daily page shows above the categories.
    highlights = [clean(h, 200) for h in (recap.get("highlights") or []) if isinstance(h, str) and h.strip()]
    tldr_html = ""
    if highlights:
        lis = "".join(f'<li style="margin:4px 0">{html.escape(h)}</li>' for h in highlights)
        tldr_html = (
            '<div style="margin:6px 0 14px;padding:12px 14px;border-radius:8px;background:#f6f8fa">'
            '<div style="font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;'
            'color:#1a6dd6;margin-bottom:6px">In 30 seconds</div>'
            f'<ul style="font-size:13px;line-height:1.5;color:#333;padding-left:18px;margin:0">{lis}</ul></div>'
        )
    intro_paras = [clean(p, 500) for p in (recap.get("intro") or []) if isinstance(p, str) and p.strip()]
    intro_html = "".join(
        f'<p style="font-size:14px;line-height:1.6;color:#333;margin:0 0 10px">{html.escape(p)}</p>'
        for p in intro_paras[:2]
    )

    # Themed categories: each article links to its /story/<sid> permalink, carries
    # its source and one-line recap summary, and keeps the one-tap feedback row.
    cat_html: list[str] = []
    for idx, c in enumerate(cats, 1):
        name = html.escape(clean(c.get("name", ""), 80))
        csum = html.escape(clean(c.get("summary", ""), 220))
        arts: list[str] = []
        raw_articles = [a for a in (c.get("articles") or []) if isinstance(a, dict)]
        for a in raw_articles:
            url = a.get("url", "")
            title = html.escape(clean(a.get("title", ""), 140))
            src = html.escape(clean(source_name(a.get("source", "")), 40))
            asum = html.escape(clean(a.get("summary", ""), 180))
            arts.append(
                '<tr><td style="padding:11px 0;border-bottom:1px solid #eee">'
                f'<div style="font-size:15px;font-weight:600;line-height:1.35">'
                f'<a href="{html.escape(story_url(cfg, url))}" '
                f'style="color:#111;text-decoration:none">{title}</a></div>'
                f'<div style="font-size:12px;color:#888;margin-top:3px">{src}</div>'
                + (f'<div style="font-size:13px;color:#444;margin-top:4px">{asum}</div>' if asum else "")
                + feedback_row(cfg, url)
                + "</td></tr>"
            )
        article_count = len(raw_articles)
        item_label = "item" if article_count == 1 else "items"
        cat_html.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:24px 0 2px;border-top:1px solid #d8dee4;background:#f6f8fa">'
            '<tr><td style="padding:10px 12px">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;'
            f'color:#57606a">Theme {idx} · {article_count} {item_label}</div>'
            f'<div style="font-size:16px;font-weight:700;line-height:1.35;color:#111;margin-top:2px">{name}</div>'
            + (f'<div style="font-size:13px;line-height:1.45;color:#555;margin-top:3px">{csum}</div>' if csum else "")
            + "</td></tr></table>"
            + f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(arts)}</table>'
        )
    cats_html = "".join(cat_html)

    thread_html = ""
    if threads:
        tr = []
        for t in threads:
            wn = html.escape(clean(t["whats_new"], 220))
            label = html.escape(t["label"])
            tr.append(
                f'<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0">'
                f'<div style="font-size:14px;font-weight:600">'
                f'<a href="{html.escape(storyline_url(cfg, t["slug"]))}" '
                f'style="color:#1a6dd6;text-decoration:none">{label} →</a></div>'
                f'<div style="font-size:13px;color:#444;margin-top:3px">{wn}</div></td></tr>'
            )
        thread_html = (
            '<h2 style="font-size:16px;margin:28px 0 6px">🧵 Continuing threads</h2>'
            '<div style="font-size:12px;color:#888;margin-bottom:6px">'
            "What happened next with stories you've been following.</div>"
            f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(tr)}</table>'
        )

    feed_url = f"{cfg['site_base'].rstrip('/')}/?utm_source={cfg['utm_source']}"
    daily_page = f"{cfg['site_base'].rstrip('/')}/daily/{recap_date}?utm_source={cfg['utm_source']}"
    weekly_url = f"{cfg['site_base'].rstrip('/')}/weekly?utm_source={cfg['utm_source']}"
    unsub = unsubscribe_html(cfg)
    n_cats = len(cats)
    sub_meta = f"{n} picks · {n_cats} theme{'s' if n_cats != 1 else ''} · ~{mins} min · one shared ranking, no filter bubble"
    preheader = html.escape(_preheader(recap, articles))
    body = f"""\
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:#fff">{preheader}{PREHEADER_PAD}</div>
<div style="max-width:640px;margin:0 auto;padding:24px 18px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111">
  <div style="font-size:12px;color:#999;letter-spacing:.04em;text-transform:uppercase">{logo_img(cfg)}LLM Digest · {recap_date}</div>
  <h1 style="font-size:20px;margin:6px 0 2px">Your AI brief</h1>
  <div style="font-size:13px;color:#777;margin-bottom:12px">{sub_meta}</div>
  {tldr_html}
  {intro_html}
  {cats_html}
  {thread_html}
  <div style="margin:26px 0 10px;padding:12px;border-radius:8px;background:#f6f8fa;text-align:center;font-size:14px;font-weight:600;color:#1a7f37">✅ You're caught up.</div>
  <div style="font-size:12px;color:#999;margin-top:18px;line-height:1.6">
    <a href="{html.escape(daily_page)}" style="color:#1a6dd6">Read this on the web</a> ·
    <a href="{html.escape(feed_url)}" style="color:#1a6dd6">Open the full feed</a> ·
    <a href="{html.escape(weekly_url)}" style="color:#1a6dd6">This week's recap</a>{unsub}<br>
    The finishable AI feed for platform engineers — 10 minutes a day, with memory.
  </div>
</div>"""
    return subject, body


def render_weekly(cfg: dict, wk: dict, threads: list[dict], wiki: list[dict]) -> tuple[str, str]:
    """Returns (subject, html_body) for the weekly recap."""
    title = wk.get("title") or f"What happened in AI — week {wk.get('week','')}"
    subject = title
    base = cfg["site_base"].rstrip("/")
    utm = cfg["utm_source"]

    intro = wk.get("intro") or []
    intro_html = "".join(
        f'<p style="font-size:14px;line-height:1.6;color:#333;margin:0 0 10px">{html.escape(p)}</p>'
        for p in intro[:2]
    )

    highlights = wk.get("highlights") or []
    hl_html = ""
    if highlights:
        lis = "".join(f'<li style="margin:4px 0">{html.escape(h)}</li>' for h in highlights)
        hl_html = (
            '<h2 style="font-size:16px;margin:22px 0 6px">⭐ Highlights</h2>'
            f'<ul style="font-size:14px;line-height:1.5;color:#333;padding-left:20px;margin:0">{lis}</ul>'
        )

    fav = reader_favorites(int(cfg["weekly"].get("max_favorites", 3)))
    fav_html = ""
    if fav:
        chips = " · ".join(
            f'<span style="color:#333;font-weight:600">{html.escape(source_name(s))}</span>' for s, _ in fav
        )
        fav_html = (
            '<div style="margin:18px 0 4px;padding:10px 12px;border-radius:8px;background:#f6f8fa;font-size:13px;color:#555">'
            f"📈 <strong>Reader favorites this week</strong> — sources you clicked most: {chips}</div>"
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
                f'<li style="margin:5px 0;font-size:13px;line-height:1.4">'
                f'<a href="{html.escape(story_url(cfg, url))}" style="color:#111;text-decoration:none">{t}</a>'
                f' <span style="color:#999">· {src}</span></li>'
            )
        cat_html.append(
            f'<div style="margin:14px 0"><div style="font-size:15px;font-weight:600">{html.escape(c.get("name",""))}</div>'
            f'<div style="font-size:13px;color:#666;margin:2px 0 4px">{html.escape(clean(c.get("summary",""), 220))}</div>'
            f'<ul style="padding-left:18px;margin:0;list-style:disc">{"".join(arts)}</ul></div>'
        )
    cats_section = (
        '<h2 style="font-size:16px;margin:24px 0 4px">📚 By theme</h2>' + "".join(cat_html) if cat_html else ""
    )

    thread_html = ""
    if threads:
        tr = []
        for t in threads:
            wn = html.escape(clean(t["whats_new"], 220))
            tr.append(
                f'<tr><td style="padding:9px 0;border-bottom:1px solid #f0f0f0">'
                f'<div style="font-size:14px;font-weight:600"><a href="{html.escape(storyline_url(cfg, t["slug"]))}" '
                f'style="color:#1a6dd6;text-decoration:none">{html.escape(t["label"])} →</a></div>'
                f'<div style="font-size:13px;color:#444;margin-top:3px">{wn}</div></td></tr>'
            )
        thread_html = (
            '<h2 style="font-size:16px;margin:26px 0 6px">🧵 Storylines that moved this week</h2>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(tr)}</table>'
        )

    wiki_html = ""
    if wiki:
        wr = []
        for w in wiki:
            topic_url = f"{base}/topic/{w['slug']}?utm_source={utm}"
            kind = "obstacle" if w["kind"] == "obstacle" else "solution"
            wr.append(
                f'<tr><td style="padding:9px 0;border-bottom:1px solid #f0f0f0">'
                f'<div style="font-size:14px;font-weight:600"><a href="{html.escape(topic_url)}" '
                f'style="color:#7a3fb8;text-decoration:none">{html.escape(clean(w["title"], 120))} →</a>'
                f'<span style="font-size:11px;color:#999;font-weight:400"> · {kind}</span></div>'
                f'<div style="font-size:13px;color:#444;margin-top:3px">{html.escape(clean(w["summary"], 200))}</div></td></tr>'
            )
        wiki_html = (
            '<h2 style="font-size:16px;margin:26px 0 6px">🗺️ New in the knowledge map</h2>'
            '<div style="font-size:12px;color:#888;margin-bottom:6px">'
            "Patterns and solutions that emerged this week — the durable layer, not the news.</div>"
            f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(wr)}</table>'
        )

    feed_url = f"{base}/?utm_source={utm}"
    weekly_page = f"{base}/weekly/{wk.get('week','')}?utm_source={utm}"
    unsub = unsubscribe_html(cfg)
    pre = clean(highlights[0], 110) if highlights else clean(" ".join(intro[:1]), 110)
    preheader = html.escape(f"{pre} — your weekly catch-up.")
    body = f"""\
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:#fff">{preheader}{PREHEADER_PAD}</div>
<div style="max-width:640px;margin:0 auto;padding:24px 18px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111">
  <div style="font-size:12px;color:#999;letter-spacing:.04em;text-transform:uppercase">{logo_img(cfg)}LLM Digest · Weekly recap</div>
  <h1 style="font-size:21px;margin:6px 0 10px">{html.escape(title)}</h1>
  {intro_html}
  {hl_html}
  {fav_html}
  {cats_section}
  {thread_html}
  {wiki_html}
  <div style="font-size:12px;color:#999;margin-top:22px;line-height:1.6">
    <a href="{html.escape(weekly_page)}" style="color:#1a6dd6">Read the full recap</a> ·
    <a href="{html.escape(feed_url)}" style="color:#1a6dd6">Open the feed</a>{unsub}<br>
    The finishable AI feed for platform engineers — 10 minutes a day, with memory.
  </div>
</div>"""
    return subject, body


# --------------------------------------------------------------------------- #
# Provider send (broadcast)
# --------------------------------------------------------------------------- #
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


def send_broadcast(cfg: dict, api_key: str, subject: str, html_body: str, name: str = "", kind: str = "daily") -> bool:
    """Send the broadcast. Returns True if sent, False for a clean no-op
    (e.g. the recipient segment is empty — nothing to send, not an error).

    ``name`` is the provider-side internal label shown in the dashboard
    broadcast list (distinct from the subscriber-facing ``subject``). Without
    it Resend lists every broadcast as "Untitled". ``kind`` selects the Resend
    Topic the send scopes to (daily vs weekly), so per-digest opt-outs hold."""
    provider = (cfg.get("provider") or "buttondown").lower()
    text_body = html_to_text(html_body)
    if provider == "buttondown":
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
        segment_id = (os.getenv("EMAIL_SEGMENT_ID") or os.getenv("EMAIL_AUDIENCE_ID") or "").strip()
        from_addr = os.getenv("EMAIL_FROM", "").strip()
        if not segment_id or not from_addr:
            raise RuntimeError("resend requires EMAIL_SEGMENT_ID and EMAIL_FROM")
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


def build_daily(cfg: dict, state: dict) -> tuple[str, str, list[dict], str] | None:
    """Returns (subject, body, threads, recap_date), or None when there is no
    daily recap to send (clean no-op)."""
    recap = _latest_daily()
    if not recap:
        return None
    threads = storyline_deltas(state, int(cfg["daily"]["max_threads"]))
    subject, body = render_daily(cfg, recap, threads)
    return subject, body, threads, (recap.get("date") or "").strip()


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


def build_weekly(cfg: dict) -> tuple[str, str, dict, int, int]:
    wk = _latest_weekly()
    if not wk:
        raise RuntimeError("no weekly recap to render")
    start, end = wk.get("start", ""), wk.get("end", "")
    threads = storylines_in_window(start, end, int(cfg["weekly"]["max_threads"]))
    wiki = wiki_in_window(start, end, int(cfg["weekly"]["max_wiki"]))
    subject, body = render_weekly(cfg, wk, threads, wiki)
    return subject, body, wk, len(threads), len(wiki)


def main() -> int:
    ap = argparse.ArgumentParser(description="Send the email digest")
    ap.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    ap.add_argument("--dry-run", action="store_true", help="render to stdout, never send, never touch state")
    ap.add_argument("--force", action="store_true", help="ignore the already-sent guard")
    args = ap.parse_args()

    cfg = load_config()
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")

    # Build the email + figure out the idempotency guard for this kind.
    if args.kind == "weekly":
        subject, body, wk, n_threads, n_wiki = build_weekly(cfg)
        week_key = wk.get("week", "")
        already_sent = state.get("weekly", {}).get("last_sent_week") == week_key
        guard_reason = "already_sent_week"
        summary = f"week={week_key} threads={n_threads} wiki={n_wiki}"
        broadcast_name = f"Weekly recap — {week_key or today}"
    else:
        built = build_daily(cfg, state)
        if built is None:
            # No curated recap committed yet — no-op cleanly (never the raw feed).
            print("email_send_skipped=true kind=daily reason=no_recap")
            return 0
        subject, body, threads, recap_date = built
        # Guard on the recap's own date, not the calendar day: send the latest
        # recap once, re-send only when a newer recap appears.
        already_sent = state.get("daily", {}).get("last_sent_date") == recap_date
        guard_reason = "already_sent_recap"
        summary = f"recap_date={recap_date} threads={len(threads)}"
        broadcast_name = f"Daily brief — {recap_date or today}"

    if args.dry_run:
        print(f"<!-- subject: {subject} -->")
        print(body)
        print(f"\n<!-- kind={args.kind} {summary} -->")
        return 0

    if already_sent and not args.force:
        print(f"email_skipped=true kind={args.kind} reason={guard_reason}")
        return 0

    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    enabled = bool(cfg.get("enabled")) and bool(api_key)
    if not enabled:
        # Secrets-gated no-op, like PostHog when unconfigured.
        print("email_send_skipped=true reason=disabled_or_no_api_key")
        return 0

    if not send_broadcast(cfg, api_key, subject, body, broadcast_name, kind=args.kind):
        # Nothing was sent (e.g. empty recipient segment). Leave the cursor
        # untouched so the next run re-attempts once contacts exist.
        print(f"email_send_skipped=true kind={args.kind} reason=nothing_sent")
        return 0

    # Advance the cursor only after a successful send, so a failure re-sends
    # rather than silently dropping a period.
    if args.kind == "weekly":
        # Weekly is window-based (see storylines_in_window); the cursor only
        # records last_sent_week for the Friday-cron idempotency guard.
        state["weekly"] = {"last_sent_week": week_key}
    else:
        new_seen = set(state.get("storylines", {}).get("seen_sids") or [])
        newest = state.get("storylines", {}).get("sent_through") or ""
        for t in threads:
            new_seen.update(t["member_sids"])
            if t["last_updated"] > newest:
                newest = t["last_updated"]
        state["daily"] = {"last_sent_date": recap_date}
        state["storylines"] = {"sent_through": newest, "seen_sids": sorted(new_seen)}
    save_state(state)

    print(f"email_sent=true kind={args.kind} {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
