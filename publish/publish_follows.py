#!/usr/bin/env python3
"""Storyline follow alerts — email each follower when a story they follow moves.

Readers follow a storyline by email from its page (``lib/follow.js`` via ``/api/subscribe``), which
stores the slug in the Resend contact property ``followed_storylines`` and puts
the contact in the "Storyline followers" segment. This job finds storylines
whose content-based ``last_updated`` passed the committed cursor
(``data/email/state.json → follows.sent_through``), then sends every follower
one personal email covering just the stories they follow that moved.

Broadcasts send one body to a whole segment, so per-follower content goes out
as batch transactional emails (``/emails/batch``). Each carries signed unfollow
links (per story and "all") plus a one-click ``List-Unsubscribe`` header, and
contacts that unsubscribed globally are skipped.

Secrets-gated like the digest: no ``EMAIL_API_KEY`` / ``EMAIL_FROM``, provider
not Resend, or ``config/email.yaml → follows.enabled: false`` ⇒ clean no-op.
The first run only initializes the cursor, so launch never mails backlog.

Usage:
    python3 publish/publish_follows.py            # send (if configured)
    python3 publish/publish_follows.py --dry-run  # print what would move, send nothing
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish.publish_email import (  # noqa: E402
    html_to_text,
    load_config,
    load_state,
    logo_img,
    narrative_copy,
    save_state,
    storyline_url,
)

API = "https://api.resend.com"
FOLLOW_PROPERTY = "followed_storylines"
FOLLOWERS_SEGMENT_NAME = "Storyline followers"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
READER_ID_RE = re.compile(r"^anon_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
BATCH_SIZE = 100
REQUEST_PAUSE_S = 0.6  # Resend's default limit is 2 requests/second


# --------------------------------------------------------------------------- #
# Pure helpers (tested)
# --------------------------------------------------------------------------- #
def parse_follows(value: object) -> list[str]:
    out: list[str] = []
    for part in str(value or "").split(","):
        slug = part.strip()
        if SLUG_RE.match(slug) and slug not in out:
            out.append(slug)
    return out


def unfollow_token(api_key: str, contact_id: str, slug: str) -> str:
    """Must match ``unfollowToken`` in lib/follow.js."""
    msg = f"unfollow:{contact_id}:{slug}".encode()
    return hmac.new(api_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


def unfollow_url(cfg: dict, api_key: str, contact_id: str, slug: str) -> str:
    base = cfg["site_base"].rstrip("/")
    token = unfollow_token(api_key, contact_id, slug)
    return f"{base}/api/subscribe?c={quote(contact_id, safe='')}&s={quote(slug, safe='*')}&t={token}"


def moved_storylines(since: str) -> list[dict]:
    """Storylines whose ``last_updated`` is after ``since``, newest first."""
    p = ROOT / "data" / "storylines" / "index.json"
    try:
        rows = json.loads(p.read_text(encoding="utf-8")).get("storylines") or []
    except Exception:
        return []
    moved = [
        r for r in rows
        if isinstance(r, dict) and SLUG_RE.match(str(r.get("slug") or ""))
        and str(r.get("last_updated") or "") > since
    ]
    return sorted(moved, key=lambda r: str(r.get("last_updated") or ""), reverse=True)


def latest_storyline_update() -> str:
    return max((str(r.get("last_updated") or "") for r in moved_storylines("")), default="")


def render_follow_email(cfg: dict, api_key: str, contact: dict, threads: list[dict]) -> tuple[str, str]:
    """(subject, html) for one follower and the followed threads that moved."""
    rid = contact.get("reader_id") or ""
    rid_param = f"&rid={rid}" if READER_ID_RE.match(rid) else ""
    if len(threads) == 1:
        subject = f"{threads[0].get('label') or threads[0]['slug']} moved — LLM Digest"
    else:
        subject = f"{len(threads)} stories you follow moved — LLM Digest"

    blocks = []
    for t in threads:
        slug = t["slug"]
        label = t.get("label") or slug
        copy = narrative_copy(slug, str(t.get("last_updated") or ""), str(t.get("latest_title") or ""))
        link = storyline_url(cfg, slug) + rid_param
        stop = unfollow_url(cfg, api_key, contact["id"], slug)
        blocks.append(
            '<div style="margin:0 0 18px">'
            f'<a href="{html.escape(link)}" style="font-size:17px;font-weight:600;color:#1a1a1a;text-decoration:none">'
            f"{html.escape(label)}</a>"
            f'<div style="font-size:14px;line-height:1.5;color:#333;margin-top:4px">{html.escape(copy)}</div>'
            f'<div style="font-size:12px;margin-top:6px"><a href="{html.escape(link)}" style="color:#2563eb">'
            "See what changed →</a>"
            f'<span style="color:#ccc"> · </span><a href="{html.escape(stop)}" style="color:#999">'
            "Unfollow this story</a></div></div>"
        )
    stop_all = unfollow_url(cfg, api_key, contact["id"], "*")
    body = (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;max-width:560px;margin:0 auto;padding:16px">'
        f'<div style="font-size:14px;font-weight:600;margin-bottom:14px">{logo_img(cfg)}LLM Digest</div>'
        '<div style="font-size:13px;color:#666;margin-bottom:16px">'
        "A story you follow picked up new coverage.</div>"
        + "".join(blocks)
        + '<div style="font-size:12px;color:#999;border-top:1px solid #eee;padding-top:10px;margin-top:8px">'
        "You get this because you followed these stories on llm-digest.com. "
        f'<a href="{html.escape(stop_all)}" style="color:#999">Stop all story emails</a></div></div>'
    )
    return subject, body


# --------------------------------------------------------------------------- #
# Provider calls
# --------------------------------------------------------------------------- #
def _get(api_key: str, path: str, **params) -> requests.Response:
    time.sleep(REQUEST_PAUSE_S)
    return requests.get(f"{API}{path}", headers={"Authorization": f"Bearer {api_key}"}, params=params, timeout=30)


def followers_segment_id(api_key: str) -> str:
    configured = os.getenv("EMAIL_SEGMENT_ID_FOLLOWERS", "").strip()
    if configured:
        return configured
    r = _get(api_key, "/segments")
    r.raise_for_status()
    for seg in r.json().get("data") or []:
        if seg.get("name") == FOLLOWERS_SEGMENT_NAME:
            return str(seg.get("id") or "")
    return ""  # nobody has followed yet — lib/follow.js creates it on first follow


def list_followers(api_key: str, segment_id: str) -> list[dict]:
    ids: list[str] = []
    after = None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        r = _get(api_key, f"/segments/{segment_id}/contacts", **params)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("data") or []
        ids.extend(str(c["id"]) for c in rows if c.get("id"))
        if not payload.get("has_more") or not rows:
            break
        after = rows[-1]["id"]

    followers = []
    for contact_id in ids:
        r = _get(api_key, f"/contacts/{contact_id}")
        if r.status_code == 404:
            continue
        r.raise_for_status()
        c = r.json()
        props = c.get("properties") or {}

        def prop(key: str) -> str:
            v = props.get(key)
            return str((v.get("value") if isinstance(v, dict) else v) or "")

        followers.append({
            "id": contact_id,
            "email": c.get("email") or "",
            "unsubscribed": bool(c.get("unsubscribed")),
            "follows": parse_follows(prop(FOLLOW_PROPERTY)),
            "reader_id": prop("reader_id"),
        })
    return followers


def send_batch(api_key: str, messages: list[dict], idempotency_prefix: str) -> None:
    for i in range(0, len(messages), BATCH_SIZE):
        chunk = messages[i:i + BATCH_SIZE]
        r = requests.post(
            f"{API}/emails/batch",
            headers={
                "Authorization": f"Bearer {api_key}",
                # A re-run after a partial failure must not double-send a chunk.
                "Idempotency-Key": f"{idempotency_prefix}-{i // BATCH_SIZE}",
            },
            json=chunk,
            timeout=60,
        )
        r.raise_for_status()
        time.sleep(REQUEST_PAUSE_S)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_messages(cfg: dict, api_key: str, from_addr: str, followers: list[dict], moved: list[dict]) -> list[dict]:
    by_slug = {t["slug"]: t for t in moved}
    messages = []
    for f in followers:
        if f["unsubscribed"] or not f["email"]:
            continue
        threads = [by_slug[s] for s in f["follows"] if s in by_slug]
        if not threads:
            continue
        threads.sort(key=lambda t: str(t.get("last_updated") or ""), reverse=True)
        subject, body = render_follow_email(cfg, api_key, f, threads)
        stop_all = unfollow_url(cfg, api_key, f["id"], "*")
        messages.append({
            "from": from_addr,
            "to": [f["email"]],
            "subject": subject,
            "html": body,
            "text": html_to_text(body),
            "headers": {
                "List-Unsubscribe": f"<{stop_all}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
            "tags": [{"name": "kind", "value": "storyline_follow"}],
        })
    return messages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print what moved, never send or touch state")
    args = ap.parse_args()

    cfg = load_config()
    state = load_state()
    cursor = str((state.get("follows") or {}).get("sent_through") or "")

    if args.dry_run:
        moved = moved_storylines(cursor)
        print(f"follows_dry_run=true cursor={cursor or 'unset'} moved={','.join(t['slug'] for t in moved)}")
        return 0

    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    from_addr = os.getenv("EMAIL_FROM", "").strip()
    follows_cfg = cfg.get("follows") if isinstance(cfg.get("follows"), dict) else {}
    enabled = (
        bool(cfg.get("enabled")) and bool(follows_cfg.get("enabled", True))
        and (cfg.get("provider") or "").lower() == "resend" and bool(api_key) and bool(from_addr)
    )
    if not enabled:
        print("follows_send_skipped=true reason=disabled_or_unconfigured")
        return 0

    if not cursor:
        # First run: start from now so launch never mails the whole backlog.
        state["follows"] = {"sent_through": latest_storyline_update()}
        save_state(state)
        print(f"follows_send_skipped=true reason=cursor_initialized sent_through={state['follows']['sent_through']}")
        return 0

    moved = moved_storylines(cursor)
    if not moved:
        print(f"follows_send_skipped=true reason=nothing_moved cursor={cursor}")
        return 0
    newest = str(moved[0].get("last_updated") or cursor)

    segment_id = followers_segment_id(api_key)
    followers = list_followers(api_key, segment_id) if segment_id else []
    messages = build_messages(cfg, api_key, from_addr, followers, moved)
    if messages:
        send_batch(api_key, messages, idempotency_prefix=f"follows-{newest}")

    # Advance only after every batch succeeded, so a failure re-sends.
    state["follows"] = {"sent_through": newest}
    save_state(state)
    print(
        f"follows_sent=true moved={len(moved)} followers={len(followers)} "
        f"emails={len(messages)} sent_through={newest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
