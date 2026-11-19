"""Community-thread sidecar for daily recaps.

The daily-thread routine (``.agents/skills/daily-thread/``) writes
``data/daily/thread/<date>.json``: the same day's news retold as a fictional
community thread, one per locale (``en`` = Reddit style, ``ko`` = DC Inside
style). This module validates that sidecar against its recap and renders it
into the static daily pages. A missing or invalid sidecar renders nothing.

CLI: ``python pipeline/recap_thread.py --check [--date YYYY-MM-DD]``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "data" / "daily"
THREAD_DIR = DAILY_DIR / "thread"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STYLES = {"en": "reddit", "ko": "dcinside"}
MAX_COMMENTS = 14
MAX_DEPTH = 2
MAX_BODY_CHARS = 2400
MAX_COMMENT_CHARS = 600

COPY = {
    "en": {
        "label": "The thread",
        "dek": "Today's recap, retold as a community thread by the agent that writes it.",
        "note": "Fictional thread written by our editor agent. Usernames and scores are made up; every fact links to a source in this recap.",
        "op": "OP",
        "points": "points",
        "sources": "Sources",
        "comments": "comments",
    },
    "ko": {
        "label": "갤러리 스레드",
        "dek": "오늘 리캡을 작성한 에이전트가 커뮤니티 글로 다시 썼습니다.",
        "note": "편집 에이전트가 쓴 가상 스레드입니다. 닉네임·IP·추천수는 지어낸 것이며, 모든 사실은 이 리캡의 출처로 연결됩니다.",
        "op": "글쓴이",
        "points": "추천",
        "sources": "출처",
        "comments": "댓글",
    },
}


def _lines(value) -> list[str]:
    if isinstance(value, str):
        value = [p for p in re.split(r"\n\s*\n", value)]
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, str) and str(v).strip()]


def recap_urls(recap: dict) -> set[str]:
    urls = set()
    for cat in recap.get("categories") or []:
        for art in cat.get("articles") or []:
            if isinstance(art, dict) and art.get("url"):
                urls.add(str(art["url"]))
    return urls


def validate(sidecar: dict, recap: dict) -> list[str]:
    """Return a list of problems; empty means publishable."""
    errs: list[str] = []
    if not isinstance(sidecar, dict):
        return ["sidecar is not an object"]
    if sidecar.get("date") != recap.get("date"):
        errs.append(f"date {sidecar.get('date')!r} != recap date {recap.get('date')!r}")
    threads = sidecar.get("threads")
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
        body = _lines(c.get("body"))
        if not body:
            errs.append(f"{where}: body required")
        if sum(len(b) for b in body) > MAX_COMMENT_CHARS:
            errs.append(f"{where}: body over {MAX_COMMENT_CHARS} chars")
        check_refs(c.get("refs"), where)
        replies = c.get("replies") or []
        if replies and depth >= MAX_DEPTH:
            errs.append(f"{where}: replies nested deeper than {MAX_DEPTH}")
        for i, r in enumerate(replies if isinstance(replies, list) else []):
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
        body = _lines(t.get("body"))
        if not body:
            errs.append(f"{where}: body required")
        if sum(len(b) for b in body) > MAX_BODY_CHARS:
            errs.append(f"{where}: body over {MAX_BODY_CHARS} chars")
        if not t.get("refs"):
            errs.append(f"{where}: refs required (link the facts the post uses)")
        check_refs(t.get("refs"), where)
        comments = t.get("comments") or []
        count = [0]
        for i, c in enumerate(comments if isinstance(comments, list) else []):
            check_comment(c, f"{where}.comments[{i}]", 1, count)
        if count[0] > MAX_COMMENTS:
            errs.append(f"{where}: {count[0]} comments, max {MAX_COMMENTS}")
    return errs


def load_thread(day: str, recap: dict) -> dict | None:
    path = THREAD_DIR / f"{day}.json"
    if not path.exists():
        return None
    try:
        sidecar = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"warning: recap thread unreadable path={path} err={exc}", file=sys.stderr)
        return None
    errs = validate(sidecar, recap)
    if errs:
        print(f"warning: recap thread invalid date={day} errors={errs[:3]}", file=sys.stderr)
        return None
    return sidecar


def _paras(lines: list[str]) -> str:
    return "".join(f"<p>{escape(line)}</p>" for line in lines)


def _refs_html(refs, titles: dict[str, str], copy: dict) -> str:
    if not refs:
        return ""
    links = "".join(
        f'<li><a href="{escape(u)}" rel="noopener" data-track="thread-ref">'
        f"{escape(titles.get(u, u))}</a></li>"
        for u in refs
    )
    return f'<details class="thread-refs"><summary>{escape(copy["sources"])} ({len(refs)})</summary><ul>{links}</ul></details>'


def _author_html(c: dict, style: str, copy: dict) -> str:
    name = escape(str(c.get("author")))
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
        f'<div class="thread-body">{_paras(_lines(c.get("body")))}</div>'
        f"{_refs_html(c.get('refs'), titles, copy)}{replies_html}</div>"
    )


def _count(comments) -> int:
    return sum(1 + _count(c.get("replies") or []) for c in comments or [])


def render_thread(sidecar: dict | None, recap: dict, locale: str = "en") -> str:
    if not sidecar:
        return ""
    t = (sidecar.get("threads") or {}).get(locale)
    if not isinstance(t, dict):
        return ""
    copy = COPY.get(locale, COPY["en"])
    style = t.get("style") or STYLES.get(locale, "reddit")
    titles = {
        str(a.get("url")): str(a.get("title") or a.get("url"))
        for cat in recap.get("categories") or []
        for a in cat.get("articles") or []
        if isinstance(a, dict)
    }
    op = {"author": t.get("author"), "tag": t.get("tag"), "is_op": False}
    stats = []
    if isinstance(t.get("score"), int):
        stats.append(f'{int(t["score"])} {copy["points"]}')
    stats.append(f'{_count(t.get("comments"))} {copy["comments"]}')
    comments = "".join(_comment_html(c, style, titles, copy) for c in t.get("comments") or [])
    lang = ' lang="ko"' if locale == "ko" else ' lang="en"'
    return (
        f'<section class="recap-thread thread-{escape(style)}" id="thread" aria-label="{escape(copy["label"])}"{lang}>'
        f'<p class="thread-label">{escape(copy["label"])}</p>'
        f'<p class="thread-dek">{escape(copy["dek"])}</p>'
        f'<details class="thread-card" open><summary>'
        f'<span class="thread-board">{escape(str(t.get("board")))}</span>'
        f'<span class="thread-title">{escape(str(t.get("title")))}</span>'
        f'<span class="thread-meta">{_author_html(op, style, copy)}'
        f'<span class="thread-score">{escape(" · ".join(stats))}</span></span></summary>'
        f'<div class="thread-post">{_paras(_lines(t.get("body")))}'
        f"{_refs_html(t.get('refs'), titles, copy)}</div>"
        f'<div class="thread-comments">{comments}</div></details>'
        f'<p class="thread-note">{escape(copy["note"])}</p></section>'
    )


THREAD_CSS = """\
    .recap-thread { margin:2rem 0 1.4rem; padding:1.4rem 0 0; border-top:1px solid var(--border); }
    .thread-label { margin:0 0 .3rem; font-family:var(--font-mono); font-size:.78rem; font-weight:700; color:var(--accent); }
    .thread-dek { margin:0 0 .9rem; color:var(--muted); font-size:.9rem; }
    .thread-card { border:1px solid var(--border); border-radius:6px; background:var(--card); }
    .recap-thread .thread-card > summary { display:grid; margin:0; border-radius:6px 6px 0 0; gap:.3rem; padding:.95rem 1.05rem; cursor:pointer; list-style:none;
      border-bottom:1px solid var(--border); }
    .thread-card > summary::-webkit-details-marker { display:none; }
    .thread-board { font-family:var(--font-mono); font-size:.72rem; color:var(--muted); }
    .thread-title { font-size:1.12rem; font-weight:700; line-height:1.3; }
    .thread-meta { display:flex; flex-wrap:wrap; align-items:baseline; gap:.2rem .6rem; font-size:.78rem; color:var(--muted); }
    .thread-author { font-weight:600; color:var(--fg); }
    .thread-tag { margin-left:.15rem; font-weight:400; color:var(--muted); }
    .thread-flair { padding:0 .35rem; border:1px solid var(--border); border-radius:3px; font-size:.7rem; }
    .thread-op { padding:0 .35rem; border-radius:3px; background:var(--accent); color:#fff; font-size:.68rem; font-weight:700; }
    .thread-score { font-family:var(--font-mono); font-size:.72rem; }
    .thread-post { padding:.9rem 1.05rem .6rem; }
    .thread-post p, .thread-body p { margin:0 0 .55rem; line-height:1.58; font-size:.94rem; white-space:pre-line; }
    .thread-comments { padding:.2rem 1.05rem .9rem; }
    .thread-comment { padding:.65rem 0 .1rem; border-top:1px solid var(--border); }
    .thread-replies { margin-left:.9rem; padding-left:.85rem; border-left:2px solid var(--border); }
    .thread-replies .thread-comment { border-top:0; }
    .thread-comment.is-op > .thread-body { border-left:2px solid var(--accent); padding-left:.6rem; }
    .thread-body { margin-top:.3rem; }
    .recap-thread details.thread-card { padding:0; overflow:visible; }
    .recap-thread details > :not(summary) { margin:0; }
    .recap-thread .thread-card > summary::after { display:none; }
    .recap-thread details.thread-refs > ul { margin:.3rem 0 0; padding-left:1.1rem; }
    .recap-thread details.thread-refs { margin:.1rem 0 .5rem; padding:0; border:0; border-radius:0;
      background:transparent; box-shadow:none; font-size:.76rem; color:var(--muted); }
    .recap-thread details.thread-refs > summary { display:inline-flex; padding:0; margin:0; border:0;
      background:transparent; font-size:.76rem; font-weight:500; color:var(--muted); cursor:pointer; list-style:none; }
    .recap-thread details.thread-refs > summary::-webkit-details-marker { display:none; }
    .recap-thread details.thread-refs > summary::before { content:"↳ "; }
    .recap-thread details.thread-refs > summary::after { content:none; display:none; }
    .thread-note { margin:.7rem 0 0; color:var(--muted); font-size:.76rem; line-height:1.5; }
    .thread-dcinside .thread-card > summary { border-left:4px solid var(--signal); }
    .thread-dcinside .thread-comment { padding-top:.55rem; }
    .thread-reddit .thread-card > summary { border-left:4px solid var(--accent); }
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="validate sidecars against their recaps")
    ap.add_argument("--date", help="validate one date only")
    args = ap.parse_args(argv)
    paths = (
        [THREAD_DIR / f"{args.date}.json"]
        if args.date
        else sorted(p for p in THREAD_DIR.glob("*.json") if DATE_RE.match(p.stem))
    )
    bad = 0
    for path in paths:
        day = path.stem
        recap_path = DAILY_DIR / f"{day}.json"
        if not path.exists() or not recap_path.exists():
            print(f"THREAD_INVALID date={day} errors=['sidecar or recap missing']")
            bad += 1
            continue
        errs = validate(
            json.loads(path.read_text(encoding="utf-8")),
            json.loads(recap_path.read_text(encoding="utf-8")),
        )
        if errs:
            bad += 1
            print(f"THREAD_INVALID date={day}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"THREAD_OK date={day}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
