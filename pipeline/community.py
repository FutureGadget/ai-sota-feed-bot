"""Community posts: agent-written threads about each daily and weekly recap.

The community-thread routine (``.agents/skills/community-thread/``) writes one
post per published recap:

    data/community/daily/<YYYY-MM-DD>.json
    data/community/weekly/<YYYY-Www>.json

Each post holds one thread per locale (``en`` = Reddit style, ``ko`` = DC
Inside style) with an OP body and comments. Every fact must link to an article
in the recap the post is about. This module validates posts against their
recaps and renders the HTML fragments used by ``render_static_pages.py``
(``/community`` pages and the recap-page teaser) and the email digest. A
missing or invalid post renders nothing.

CLI: ``python pipeline/community.py --check [--kind daily|weekly] [--edition ID]``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMUNITY_DIR = ROOT / "data" / "community"

KINDS = {
    "daily": {"recap_dir": ROOT / "data" / "daily", "id_re": re.compile(r"^\d{4}-\d{2}-\d{2}$"), "id_field": "date"},
    "weekly": {"recap_dir": ROOT / "data" / "weekly", "id_re": re.compile(r"^\d{4}-W\d{2}$"), "id_field": "week"},
}
STYLES = {"en": "reddit", "ko": "dcinside"}
LOCALES = ("en", "ko")
MAX_COMMENTS = 14
MAX_DEPTH = 2
MAX_BODY_CHARS = 2400
MAX_COMMENT_CHARS = 600

COPY = {
    "en": {
        "section": "Community",
        "index_title": "Community",
        "index_dek": "Every recap, retold as a thread by the agent that writes it. Agent-written posts and comments; no reader accounts.",
        "kind": {"daily": "Daily recap thread", "weekly": "Weekly recap thread"},
        "teaser_label": "Community",
        "teaser_cta": "Read the thread",
        "recap_link": {"daily": "Read the daily recap this thread is about", "weekly": "Read the weekly recap this thread is about"},
        "comments_heading": "Comments",
        "note": "Fictional thread written by our editor agent. Usernames and scores are made up; every fact links to a source in the recap.",
        "op": "OP",
        "points": "points",
        "sources": "Sources",
        "comments": "comments",
        "empty": "No threads yet.",
    },
    "ko": {
        "section": "커뮤니티",
        "index_title": "커뮤니티",
        "index_dek": "리캡을 쓰는 에이전트가 매 리캡을 커뮤니티 글로 다시 씁니다. 글과 댓글 모두 에이전트가 작성하며, 회원 가입이나 글쓰기는 없습니다.",
        "kind": {"daily": "데일리 리캡 스레드", "weekly": "위클리 리캡 스레드"},
        "teaser_label": "커뮤니티",
        "teaser_cta": "스레드 보기",
        "recap_link": {"daily": "이 스레드의 데일리 리캡 읽기", "weekly": "이 스레드의 위클리 리캡 읽기"},
        "en_suffix": " (영문)",
        "comments_heading": "댓글",
        "note": "편집 에이전트가 쓴 가상 스레드입니다. 닉네임·IP·추천수는 지어낸 것이며, 모든 사실은 리캡의 출처로 연결됩니다.",
        "op": "글쓴이",
        "points": "추천",
        "sources": "출처",
        "comments": "댓글",
        "empty": "아직 스레드가 없습니다.",
    },
}

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# --------------------------------------------------------------------------- #
# Loading and validation
# --------------------------------------------------------------------------- #
def lines(value) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"\n\s*\n", value)
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, str) and str(v).strip()]


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def post_file(kind: str, edition: str) -> Path:
    return COMMUNITY_DIR / kind / f"{edition}.json"


def load_recap(kind: str, edition: str) -> dict | None:
    spec = KINDS.get(kind)
    if not spec or not spec["id_re"].match(str(edition)):
        return None
    data = _load_json(spec["recap_dir"] / f"{edition}.json")
    return data if isinstance(data, dict) else None


def recap_urls(recap: dict) -> set[str]:
    return {
        str(a["url"])
        for cat in recap.get("categories") or []
        for a in cat.get("articles") or []
        if isinstance(a, dict) and a.get("url")
    }


def validate(post: dict, recap: dict | None, kind: str, edition: str) -> list[str]:
    """Return a list of problems; empty means publishable."""
    errs: list[str] = []
    if kind not in KINDS:
        return [f"unknown kind {kind!r}"]
    if not isinstance(post, dict):
        return ["post is not an object"]
    if not isinstance(recap, dict):
        return [f"no published {kind} recap for {edition}"]
    if post.get("kind") != kind:
        errs.append(f"kind {post.get('kind')!r} != {kind!r}")
    if post.get("edition") != edition:
        errs.append(f"edition {post.get('edition')!r} != file id {edition!r}")
    if recap.get(KINDS[kind]["id_field"]) != edition:
        errs.append("recap id does not match edition")
    threads = post.get("threads")
    if not isinstance(threads, dict) or not threads:
        return errs + ["threads must be a non-empty object keyed by locale"]
    allowed = recap_urls(recap)

    def check_refs(refs, where):
        if refs is None:
            return
        if not isinstance(refs, list):
            errs.append(f"{where}: refs must be a list")
            return
        for url in refs:
            if url not in allowed:
                errs.append(f"{where}: ref not in recap: {url}")

    def check_comment(c, where, depth, count):
        if not isinstance(c, dict):
            errs.append(f"{where}: comment is not an object")
            return
        count[0] += 1
        if not str(c.get("author") or "").strip():
            errs.append(f"{where}: author required")
        body = lines(c.get("body"))
        if not body:
            errs.append(f"{where}: body required")
        if sum(len(b) for b in body) > MAX_COMMENT_CHARS:
            errs.append(f"{where}: body over {MAX_COMMENT_CHARS} chars")
        if "score" in c and not isinstance(c["score"], int):
            errs.append(f"{where}: score must be an integer")
        check_refs(c.get("refs"), where)
        replies = c.get("replies") or []
        if not isinstance(replies, list):
            errs.append(f"{where}: replies must be a list")
            return
        if replies and depth >= MAX_DEPTH:
            errs.append(f"{where}: replies nested deeper than {MAX_DEPTH}")
        for i, r in enumerate(replies):
            check_comment(r, f"{where}.replies[{i}]", depth + 1, count)

    for locale, t in threads.items():
        where = f"threads.{locale}"
        if locale not in STYLES:
            errs.append(f"{where}: unsupported locale (use {sorted(STYLES)})")
            continue
        if not isinstance(t, dict):
            errs.append(f"{where}: not an object")
            continue
        if t.get("style") != STYLES[locale]:
            errs.append(f"{where}: style must be {STYLES[locale]!r}")
        for key in ("board", "title", "author"):
            if not str(t.get(key) or "").strip():
                errs.append(f"{where}: {key} required")
        body = lines(t.get("body"))
        if not body:
            errs.append(f"{where}: body required")
        if sum(len(b) for b in body) > MAX_BODY_CHARS:
            errs.append(f"{where}: body over {MAX_BODY_CHARS} chars")
        if not t.get("refs"):
            errs.append(f"{where}: refs required (link the facts the post uses)")
        check_refs(t.get("refs"), where)
        comments = t.get("comments") or []
        if not isinstance(comments, list):
            errs.append(f"{where}: comments must be a list")
            continue
        count = [0]
        for i, c in enumerate(comments):
            check_comment(c, f"{where}.comments[{i}]", 1, count)
        if count[0] > MAX_COMMENTS:
            errs.append(f"{where}: {count[0]} comments, max {MAX_COMMENTS}")
    return errs


def load_post(kind: str, edition: str, recap: dict | None = None) -> dict | None:
    """Return the validated post for one recap edition, or None."""
    path = post_file(kind, edition)
    if kind not in KINDS or not path.exists():
        return None
    post = _load_json(path)
    if recap is None:
        recap = load_recap(kind, edition)
    errs = validate(post, recap, kind, edition)
    if errs:
        print(f"warning: community post invalid kind={kind} edition={edition} errors={errs[:3]}", file=sys.stderr)
        return None
    return post


def sort_date(kind: str, recap: dict) -> str:
    if kind == "weekly":
        return str(recap.get("end") or recap.get("week") or "")
    return str(recap.get("date") or "")


def iter_posts() -> list[dict]:
    """All valid posts, newest first: ``{kind, edition, post, recap}``."""
    rows = []
    for kind, spec in KINDS.items():
        folder = COMMUNITY_DIR / kind
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            edition = path.stem
            if not spec["id_re"].match(edition):
                continue
            recap = load_recap(kind, edition)
            post = load_post(kind, edition, recap)
            if post:
                rows.append({"kind": kind, "edition": edition, "post": post, "recap": recap})
    rows.sort(key=lambda r: (sort_date(r["kind"], r["recap"]), r["kind"] == "weekly"), reverse=True)
    return rows


# --------------------------------------------------------------------------- #
# Small helpers shared by pages and email
# --------------------------------------------------------------------------- #
def thread_for(post: dict | None, locale: str) -> dict | None:
    if not post:
        return None
    t = (post.get("threads") or {}).get(locale)
    return t if isinstance(t, dict) else None


def post_path(kind: str, edition: str, locale: str = "en") -> str:
    prefix = "/ko" if locale == "ko" else ""
    return f"{prefix}/community/{kind}/{edition}"


def recap_path(kind: str, edition: str, locale: str = "en") -> str:
    prefix = "/ko" if locale == "ko" else ""
    return f"{prefix}/{kind}/{edition}"


def localized_recap_exists(kind: str, edition: str, locale: str) -> bool:
    """True when ``data/i18n/<locale>/<kind>/<edition>.json`` is fresh."""
    path = ROOT / "data" / "i18n" / locale / kind / f"{edition}.json"
    recap = load_recap(kind, edition)
    artifact = _load_json(path) if path.exists() else None
    if not isinstance(artifact, dict) or not recap:
        return False
    import render_static_pages as render  # lazy: render imports this module

    return render.i18n_hash_matches(artifact.get("source_hash"), recap)


def comment_count(comments) -> int:
    return sum(1 + comment_count(c.get("replies") or []) for c in comments or [] if isinstance(c, dict))


def top_comment(thread: dict) -> dict | None:
    """Highest-scored top-level non-OP comment, else the first non-OP one."""
    comments = [c for c in thread.get("comments") or [] if isinstance(c, dict) and not c.get("is_op")]
    if not comments:
        return None
    scored = [c for c in comments if isinstance(c.get("score"), int)]
    return max(scored, key=lambda c: c["score"]) if scored else comments[0]


def edition_label(kind: str, recap: dict, locale: str = "en") -> str:
    try:
        if kind == "daily":
            d = date.fromisoformat(str(recap.get("date")))
            return f"{d.year}년 {d.month}월 {d.day}일" if locale == "ko" else f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
        s = date.fromisoformat(str(recap.get("start")))
        e = date.fromisoformat(str(recap.get("end")))
        if locale == "ko":
            return f"{s.year}년 {s.month}월 {s.day}일–{e.month}월 {e.day}일"
        if s.month == e.month:
            return f"{MONTHS[s.month - 1]} {s.day}–{e.day}, {e.year}"
        return f"{MONTHS[s.month - 1]} {s.day} – {MONTHS[e.month - 1]} {e.day}, {e.year}"
    except Exception:  # noqa: BLE001
        return str(recap.get(KINDS.get(kind, {}).get("id_field", "date")) or "")


def article_titles(recap: dict) -> dict[str, str]:
    return {
        str(a.get("url")): str(a.get("title") or a.get("url"))
        for cat in recap.get("categories") or []
        for a in cat.get("articles") or []
        if isinstance(a, dict)
    }


# --------------------------------------------------------------------------- #
# HTML fragments
# --------------------------------------------------------------------------- #
def _paras(items: list[str]) -> str:
    return "".join(f"<p>{escape(line)}</p>" for line in items)


def _refs_html(refs, titles: dict[str, str], copy: dict) -> str:
    if not refs:
        return ""
    links = "".join(
        f'<li><a href="{escape(u)}" rel="noopener" data-track="community-ref">'
        f"{escape(titles.get(u, u))}</a></li>"
        for u in refs
    )
    return (
        f'<details class="thread-refs"><summary>{escape(copy["sources"])} ({len(refs)})</summary>'
        f"<ul>{links}</ul></details>"
    )


def _author_html(c: dict, style: str, copy: dict) -> str:
    name = escape(str(c.get("author") or ""))
    tag = escape(str(c.get("tag") or ""))
    op = f' <span class="thread-op">{escape(copy["op"])}</span>' if c.get("is_op") else ""
    if style == "dcinside":
        tag_html = f'<span class="thread-tag">{tag}</span>' if tag else ""
        return f'<span class="thread-author">{name}{tag_html}</span>{op}'
    flair = f' <span class="thread-flair">{tag}</span>' if tag else ""
    return f'<span class="thread-author">{name}</span>{flair}{op}'


def _comment_html(c: dict, style: str, titles: dict, copy: dict) -> str:
    score = c.get("score")
    score_html = (
        f'<span class="thread-score">{int(score)} {escape(copy["points"])}</span>'
        if isinstance(score, int)
        else ""
    )
    replies = "".join(_comment_html(r, style, titles, copy) for r in c.get("replies") or [])
    replies_html = f'<div class="thread-replies">{replies}</div>' if replies else ""
    op_cls = " is-op" if c.get("is_op") else ""
    return (
        f'<div class="thread-comment{op_cls}"><div class="thread-meta">'
        f"{_author_html(c, style, copy)}{score_html}</div>"
        f'<div class="thread-body">{_paras(lines(c.get("body")))}</div>'
        f"{_refs_html(c.get('refs'), titles, copy)}{replies_html}</div>"
    )


def _stats(thread: dict, copy: dict) -> str:
    parts = []
    if isinstance(thread.get("score"), int):
        parts.append(f'{int(thread["score"])} {copy["points"]}')
    parts.append(f'{comment_count(thread.get("comments"))} {copy["comments"]}')
    return " · ".join(parts)


def render_post_body(post: dict, recap: dict, kind: str, edition: str, locale: str = "en") -> str:
    """The full thread for a ``/community/<kind>/<edition>`` page."""
    t = thread_for(post, locale)
    if not t:
        return ""
    copy = COPY.get(locale, COPY["en"])
    style = t.get("style") or STYLES.get(locale, "reddit")
    titles = article_titles(recap)
    op = {"author": t.get("author"), "tag": t.get("tag")}
    n = comment_count(t.get("comments"))
    comments = "".join(_comment_html(c, style, titles, copy) for c in t.get("comments") or [])
    # Link to the localized recap only when a fresh translation of the
    # English recap exists; otherwise to the English recap itself.
    localized = locale != "en" and localized_recap_exists(kind, edition, locale)
    recap_href = recap_path(kind, edition, locale if localized else "en")
    recap_label = copy["recap_link"][kind] + ("" if localized or locale == "en" else copy.get("en_suffix", ""))
    return (
        f'<div class="community-post thread-{escape(style)}" lang="{escape(locale)}">'
        f'<div class="thread-head"><span class="thread-board">{escape(str(t.get("board")))}</span>'
        f'<h2 class="thread-title">{escape(str(t.get("title")))}</h2>'
        f'<span class="thread-meta">{_author_html(op, style, copy)}'
        f'<span class="thread-score">{escape(_stats(t, copy))}</span></span></div>'
        f'<div class="thread-post">{_paras(lines(t.get("body")))}'
        f"{_refs_html(t.get('refs'), titles, copy)}</div>"
        f'<section class="thread-comments" aria-label="{escape(copy["comments_heading"])}">'
        f'<h3 class="thread-comments-head">{escape(copy["comments_heading"])} ({n})</h3>{comments}</section>'
        f'<p class="thread-note">{escape(copy["note"])}</p>'
        f'<p class="community-recap-link"><a href="{escape(recap_href)}" data-track="community-to-recap">'
        f'{escape(recap_label)} &rarr;</a></p></div>'
    )


def render_teaser(post: dict | None, kind: str, edition: str, locale: str = "en") -> str:
    """Compact card on a recap page that links to its community thread."""
    t = thread_for(post, locale)
    if not t:
        return ""
    copy = COPY.get(locale, COPY["en"])
    top = top_comment(t)
    quote = ""
    if top:
        first = (lines(top.get("body")) or [""])[0]
        if len(first) > 140:
            first = first[:139].rstrip() + "…"
        quote = (
            f'<span class="ct-quote"><span class="ct-quote-author">{escape(str(top.get("author")))}</span> '
            f"{escape(first)}</span>"
        )
    href = post_path(kind, edition, locale)
    n = comment_count(t.get("comments"))
    return (
        f'<aside class="community-teaser" aria-label="{escape(copy["teaser_label"])}" lang="{escape(locale)}">'
        f'<a href="{escape(href)}" data-track="community-teaser">'
        f'<span class="ct-label">{escape(copy["teaser_label"])} · {escape(str(t.get("board")))}</span>'
        f'<span class="ct-title">{escape(str(t.get("title")))}</span>{quote}'
        f'<span class="ct-meta">{n} {escape(copy["comments"])} · {escape(copy["teaser_cta"])} &rarr;</span>'
        "</a></aside>"
    )


def render_index_list(rows: list[dict], locale: str = "en") -> str:
    copy = COPY.get(locale, COPY["en"])
    items = []
    for row in rows:
        t = thread_for(row["post"], locale)
        if not t:
            continue
        kind, edition = row["kind"], row["edition"]
        items.append(
            f'<li class="community-row"><a href="{escape(post_path(kind, edition, locale))}">'
            f'<span class="cr-kind cr-{escape(kind)}">{escape(copy["kind"][kind])} · '
            f'{escape(edition_label(kind, row["recap"], locale))}</span>'
            f'<span class="cr-title">{escape(str(t.get("title")))}</span>'
            f'<span class="cr-meta">{escape(str(t.get("author")))} · {escape(_stats(t, copy))}</span>'
            "</a></li>"
        )
    if not items:
        return f'<p class="community-empty">{escape(copy["empty"])}</p>'
    return f'<ol class="community-list">{"".join(items)}</ol>'


TEASER_CSS = """\
    .community-teaser { margin:0 0 1.6rem; }
    .community-teaser a { display:grid; gap:.3rem; padding:.85rem 1rem; border:1px solid var(--border);
      border-left:4px solid var(--accent); border-radius:6px; background:var(--card); color:inherit; text-decoration:none; }
    .community-teaser a:hover, .community-teaser a:focus-visible { border-color:var(--accent); }
    .ct-label { font-family:var(--font-mono); font-size:.72rem; font-weight:700; color:var(--accent); }
    .ct-title { font-size:1.02rem; font-weight:700; line-height:1.3; }
    .ct-quote { font-size:.86rem; line-height:1.45; color:var(--muted); }
    .ct-quote-author { font-weight:600; color:var(--fg); }
    .ct-meta { font-family:var(--font-mono); font-size:.72rem; color:var(--muted); }
"""

THREAD_CSS = """\
    body { font-family:var(--font-sans); }
    main { max-width:820px; padding-left:1.35rem; padding-right:1.35rem; }
    .community-hero { margin:2.2rem 0 1.3rem; }
    .community-kicker a { color:var(--accent); text-decoration:none; }
    .community-kicker { margin:0 0 .35rem; font-family:var(--font-mono); font-size:.78rem; font-weight:700; color:var(--accent); }
    .community-hero h2 { margin:0; font-family:var(--font-display); font-size:clamp(2.2rem,5.6vw,3.4rem);
      font-weight:700; letter-spacing:-.04em; line-height:.98; }
    .community-dek { margin:.7rem 0 0; color:var(--muted); font-size:.95rem; line-height:1.55; max-width:44rem; }
    .community-post { border:1px solid var(--border); border-radius:6px; background:var(--card); margin:0 0 1.6rem; }
    .thread-head { display:grid; gap:.35rem; padding:1rem 1.1rem; border-bottom:1px solid var(--border); }
    .thread-reddit .thread-head { border-left:4px solid var(--accent); }
    .thread-dcinside .thread-head { border-left:4px solid var(--signal); }
    .thread-board { font-family:var(--font-mono); font-size:.72rem; color:var(--muted); }
    .thread-title { margin:0; font-size:1.3rem; font-weight:700; line-height:1.3; letter-spacing:-.01em; }
    .thread-meta { display:flex; flex-wrap:wrap; align-items:baseline; gap:.2rem .6rem; font-size:.78rem; color:var(--muted); }
    .thread-author { font-weight:600; color:var(--fg); }
    .thread-tag { margin-left:.15rem; font-weight:400; color:var(--muted); }
    .thread-flair { padding:0 .35rem; border:1px solid var(--border); border-radius:3px; font-size:.7rem; }
    .thread-op { padding:0 .35rem; border-radius:3px; background:var(--accent); color:#fff; font-size:.68rem; font-weight:700; }
    .thread-score { font-family:var(--font-mono); font-size:.72rem; }
    .thread-post { padding:1rem 1.1rem .6rem; }
    .thread-post p, .thread-body p { margin:0 0 .6rem; line-height:1.6; font-size:.95rem; white-space:pre-line; }
    .thread-comments { padding:.3rem 1.1rem 1rem; border-top:1px solid var(--border); }
    .thread-comments-head { margin:.6rem 0 .2rem; font-family:var(--font-mono); font-size:.78rem; font-weight:700; color:var(--muted); }
    .thread-comment { padding:.7rem 0 .1rem; border-top:1px solid var(--border); }
    .thread-comments-head + .thread-comment { border-top:0; }
    .thread-replies { margin-left:.9rem; padding-left:.85rem; border-left:2px solid var(--border); }
    .thread-replies .thread-comment { border-top:0; }
    .thread-comment.is-op > .thread-body { border-left:2px solid var(--accent); padding-left:.6rem; }
    .thread-body { margin-top:.3rem; }
    .community-post details.thread-refs { margin:.1rem 0 .55rem; padding:0; border:0; border-radius:0;
      background:transparent; box-shadow:none; overflow:visible; font-size:.76rem; color:var(--muted); }
    .community-post details.thread-refs > summary { display:inline-flex; padding:0; margin:0; border:0;
      background:transparent; font-size:.76rem; font-weight:500; color:var(--muted); cursor:pointer; list-style:none; }
    .community-post details.thread-refs > summary::-webkit-details-marker { display:none; }
    .community-post details.thread-refs > summary::before { content:"↳ "; }
    .community-post details.thread-refs > summary::after { content:none; display:none; }
    .community-post details.thread-refs > ul { margin:.3rem 0 0; padding-left:1.1rem; }
    .thread-note { margin:0; padding:.8rem 1.1rem; border-top:1px solid var(--border); color:var(--muted); font-size:.76rem; line-height:1.5; }
    .community-recap-link { margin:0; padding:.8rem 1.1rem 1rem; font-size:.9rem; font-weight:600; }
    .community-list { list-style:none; margin:0 0 2rem; padding:0; border-top:1px solid var(--border); }
    .community-row a { display:grid; gap:.3rem; padding:1rem .2rem; border-bottom:1px solid var(--border);
      color:inherit; text-decoration:none; }
    .community-row a:hover .cr-title, .community-row a:focus-visible .cr-title { color:var(--accent); }
    .cr-kind { font-family:var(--font-mono); font-size:.72rem; font-weight:700; color:var(--accent); }
    .cr-weekly { color:var(--signal); }
    .cr-title { font-size:1.1rem; font-weight:700; line-height:1.3; }
    .cr-meta { font-family:var(--font-mono); font-size:.72rem; color:var(--muted); }
    .community-empty { color:var(--muted); }
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="validate posts against their recaps")
    ap.add_argument("--kind", choices=sorted(KINDS))
    ap.add_argument("--edition", help="validate one edition (needs --kind)")
    args = ap.parse_args(argv)
    if args.edition and not args.kind:
        ap.error("--edition needs --kind")
    targets: list[tuple[str, str]] = []
    if args.edition:
        targets.append((args.kind, args.edition))
    else:
        for kind in [args.kind] if args.kind else KINDS:
            folder = COMMUNITY_DIR / kind
            if folder.is_dir():
                targets += [(kind, p.stem) for p in sorted(folder.glob("*.json"))]
    bad = 0
    for kind, edition in targets:
        path = post_file(kind, edition)
        post = _load_json(path) if path.exists() else None
        errs = (
            ["post file missing"]
            if post is None and not path.exists()
            else validate(post, load_recap(kind, edition), kind, edition)
        )
        if errs:
            bad += 1
            print(f"COMMUNITY_INVALID kind={kind} edition={edition}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"COMMUNITY_OK kind={kind} edition={edition}")
    if not targets:
        print("COMMUNITY_OK posts=0")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
