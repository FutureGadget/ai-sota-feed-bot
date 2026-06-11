"""Render daily/weekly recaps to static HTML + sitemap for SEO and link previews.

The /daily and /weekly pages are client-rendered JS shells, so crawlers and
link unfurlers see "Loading…" instead of content. This script turns the recap
JSON the pipeline already commits (``data/daily/<date>.json``,
``data/weekly/<week>.json``) into fully static, indexable pages:

- ``web/daily/<date>.html``   served at ``/daily/<date>``
- ``web/weekly/<week>.html``  served at ``/weekly/<week>``
- ``web/sitemap.xml``         served at ``/sitemap.xml``
- ``web/robots.txt``          served at ``/robots.txt``

Each page carries a real <title>, meta description, canonical URL, Open
Graph/Twitter cards, JSON-LD, and RSS autodiscovery — and mirrors the markup
and styles of the dynamic pages so the reader experience is identical.

Stale pages whose recap JSON no longer exists are pruned.

Stdlib only, like the rest of the recap tooling. Run after rebuilding the
recap indexes (build_daily_index.py / build_weekly_index.py do this
automatically):

    python pipeline/render_static_pages.py [--base-url https://example.com]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "data" / "daily"
WEEKLY_DIR = ROOT / "data" / "weekly"
WEB_DIR = ROOT / "web"

DEFAULT_BASE_URL = os.environ.get("SITE_BASE_URL", "https://www.llm-digest.com")
SITE_NAME = "LLM Digest"

DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
WEEK_FILE_RE = re.compile(r"^\d{4}-W\d{2}\.json$")
DATE_HTML_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.html$")
WEEK_HTML_RE = re.compile(r"^\d{4}-W\d{2}\.html$")

# Same look as web/daily.html / web/weekly.html so static and dynamic pages
# are indistinguishable to readers. Keep in sync when restyling those shells.
PAGE_CSS = """\
    html { font-size: 16px; -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
    :root, html[data-theme="light"] {
      --bg: #ffffff; --fg: #1a1a1a; --card: #ffffff; --border: #e5e5e5; --accent: #2563eb; --muted: #6b7280;
    }
    html[data-theme="dark"] {
      --bg: #15171c; --fg: #e8e8ea; --card: #1e2128; --border: #34373f; --accent: #5b8def; --muted: #9aa0aa;
    }
    body { margin: 0; line-height: 1.5; overflow-x: hidden; background: var(--bg); color: var(--fg); }
    *, *::before, *::after { box-sizing: border-box; }
    button, input, select, textarea { color: inherit; background: var(--card); border-color: var(--border); }
    a { color: var(--accent); }
    main { width: 100%; max-width: 860px; margin: 1rem auto; padding: 0 0.9rem 3rem; overflow-x: clip; }
    header { margin-bottom: 1rem; }
    .topbar { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
    .topbar h1 { margin: 0; font-size: 1.5rem; line-height: 1.2; overflow-wrap: anywhere; }
    menu { display: flex; flex-wrap: wrap; gap: 0.75rem; padding: 0; margin: 0.75rem 0 0; align-items: center; }
    .muted { color: var(--muted); }
    .recap-title { font-size: 1.7rem; margin: 1.2rem 0 0.2rem; line-height: 1.25; }
    .recap-range { color: var(--muted); margin: 0 0 1rem; font-size: 0.98rem; }
    .intro { font-size: 1.05rem; background: var(--card); border: 1px solid var(--border);
      border-radius: 12px; padding: 1rem 1.1rem; margin: 0 0 1.5rem; }
    .intro p { margin: 0 0 0.75rem; }
    .intro p:last-child { margin-bottom: 0; }
    .tldr { margin: 0 0 1rem; padding: 0 0 0.9rem; border-bottom: 1px solid var(--border); }
    .tldr-label { text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.72rem;
      font-weight: 600; color: var(--muted); margin: 0 0 0.55rem; }
    .tldr ul { margin: 0; padding-left: 1.15rem; display: flex; flex-direction: column; gap: 0.4rem; }
    .tldr li { font-size: 0.95rem; line-height: 1.45; }
    .toc { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 1.5rem; }
    .toc a { font-size: 0.9rem; padding: 0.3rem 0.7rem; border: 1px solid var(--border);
      border-radius: 999px; text-decoration: none; }
    .toc a:hover { border-color: var(--accent); }
    .cat { margin: 0 0 2rem; scroll-margin-top: 1rem; }
    .cat h2 { font-size: 1.25rem; margin: 0 0 0.25rem; display: flex; align-items: baseline; gap: 0.5rem; }
    .cat h2 .count { font-size: 0.85rem; color: var(--muted); font-weight: 400; }
    .cat-summary { color: var(--fg); opacity: 0.9; margin: 0 0 0.9rem; }
    .articles { display: flex; flex-direction: column; gap: 0.7rem; }
    article { border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 0.9rem; background: var(--card); }
    article h3 { margin: 0 0 0.3rem; font-size: 1.02rem; line-height: 1.35; }
    article h3 a { text-decoration: none; }
    article h3 a:hover { text-decoration: underline; }
    .art-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin-bottom: 0.3rem; }
    .badge { font-size: 0.72rem; padding: 0.1rem 0.5rem; font-weight: 500;
      border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
      border-radius: 999px; color: var(--accent);
      background: color-mix(in srgb, var(--accent) 14%, var(--card)); white-space: nowrap; }
    .art-summary { margin: 0.1rem 0 0; font-size: 0.95rem; }
    .archive { margin-left: auto; }
    footer { margin-top: 2rem; color: var(--muted); font-size: 0.85rem; }
"""

THEME_BOOT_JS = """\
    (function () {
      var t = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', t);
    })();
"""

PAGE_JS = """\
    (function () {
      function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        var btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
      }
      var btn = document.getElementById('themeToggle');
      if (btn) {
        applyTheme(document.documentElement.getAttribute('data-theme') || 'light');
        btn.addEventListener('click', function () {
          var now = document.documentElement.getAttribute('data-theme') || 'light';
          applyTheme(now === 'dark' ? 'light' : 'dark');
        });
      }
      var sel = document.getElementById('archive');
      if (sel) sel.addEventListener('change', function () { window.location.href = sel.value; });
    })();
"""


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def squeeze(text: str) -> str:
    return " ".join(str(text or "").split())


def clip(text: str, limit: int) -> str:
    text = squeeze(text)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut + "…"


def intro_paragraphs(intro) -> list[str]:
    if isinstance(intro, list):
        return [squeeze(p) for p in intro if squeeze(p)]
    return [squeeze(p) for p in re.split(r"\n{2,}", str(intro or "")) if squeeze(p)]


def recap_description(recap: dict) -> str:
    """Meta/OG description: first highlight(s) if present, else the intro."""
    highlights = [squeeze(h) for h in recap.get("highlights") or [] if squeeze(h)]
    if highlights:
        return clip(" ".join(highlights), 250)
    paras = intro_paragraphs(recap.get("intro"))
    return clip(paras[0] if paras else "", 250)


def iso_or_none(value) -> str | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


def fmt_long_date(day_id: str) -> str:
    """e.g. 'Wednesday, Jun 10, 2026' (matches the dynamic page header)."""
    try:
        d = date.fromisoformat(day_id)
    except Exception:
        return str(day_id)
    return f"{d.strftime('%A')}, {d.strftime('%b')} {d.day}, {d.year}"


def safe_http_url(value) -> str:
    s = str(value or "").strip()
    return s if s.startswith("http://") or s.startswith("https://") else "#"


def render_intro(recap: dict) -> str:
    paras = intro_paragraphs(recap.get("intro"))
    highlights = [squeeze(h) for h in recap.get("highlights") or [] if squeeze(h)]
    if not paras and not highlights:
        return ""
    tldr = ""
    if highlights:
        items = "".join(f"<li>{escape(h)}</li>" for h in highlights)
        tldr = (
            '<div class="tldr"><p class="tldr-label">In 30 seconds</p>'
            f"<ul>{items}</ul></div>"
        )
    body = "".join(f"<p>{escape(p)}</p>" for p in paras)
    return f'<div class="intro">{tldr}{body}</div>'


def render_categories(recap: dict, track: str) -> str:
    cats = [c for c in recap.get("categories") or [] if isinstance(c, dict)]
    toc = ""
    if len(cats) > 1:
        links = "".join(
            f'<a href="#{escape(str(c.get("slug") or c.get("name") or ""))}">'
            f'{escape(str(c.get("name") or ""))} ({len(c.get("articles") or [])})</a>'
            for c in cats
        )
        toc = f'<nav class="toc">{links}</nav>'

    sections = []
    for c in cats:
        arts = []
        for a in c.get("articles") or []:
            if not isinstance(a, dict):
                continue
            href = safe_http_url(a.get("url"))
            pub = iso_or_none(a.get("published"))
            pub_badge = ""
            if pub:
                d = datetime.fromisoformat(pub)
                pub_badge = f'<span class="badge">{escape(d.strftime("%b"))} {d.day}</span>'
            src_badge = (
                f'<span class="badge">{escape(str(a.get("source")))}</span>'
                if a.get("source")
                else ""
            )
            summary = (
                f'<p class="art-summary">{escape(squeeze(a.get("summary")))}</p>'
                if squeeze(a.get("summary"))
                else ""
            )
            arts.append(
                "<article>"
                f'<h3><a href="{escape(href)}" target="_blank" rel="noopener" data-track="{track}">'
                f'{escape(squeeze(a.get("title")) or "Untitled")}</a></h3>'
                f'<div class="art-meta">{src_badge}{pub_badge}</div>'
                f"{summary}</article>"
            )
        n = len(arts)
        cat_summary = (
            f'<p class="cat-summary">{escape(squeeze(c.get("summary")))}</p>'
            if squeeze(c.get("summary"))
            else ""
        )
        sections.append(
            f'<section class="cat" id="{escape(str(c.get("slug") or c.get("name") or ""))}">'
            f'<h2>{escape(str(c.get("name") or ""))} <span class="count">{n} item{"" if n == 1 else "s"}</span></h2>'
            f'{cat_summary}<div class="articles">{"".join(arts)}</div></section>'
        )
    return toc + "".join(sections)


def render_archive_select(options: list[tuple[str, str]], current: str, label: str) -> str:
    """Static archive picker; options are (href, text) pairs, newest first."""
    opts = "".join(
        f'<option value="{escape(href)}"{" selected" if href == current else ""}>{escape(text)}</option>'
        for href, text in options
    )
    return (
        f'<label class="archive muted">{escape(label)} '
        f'<select id="archive" aria-label="Choose {escape(label.lower())}">{opts}</select></label>'
    )


def render_head(*, title: str, description: str, canonical: str, published: str | None) -> str:
    og_published = (
        f'\n  <meta property="article:published_time" content="{escape(published)}" />'
        if published
        else ""
    )
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "datePublished": published,
            "mainEntityOfPage": canonical,
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": DEFAULT_BASE_URL},
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")  # recap text must not be able to close the script tag
    return f"""\
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(title)} | {escape(SITE_NAME)}</title>
  <meta name="description" content="{escape(description)}" />
  <link rel="canonical" href="{escape(canonical)}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="{escape(SITE_NAME)}" />
  <meta property="og:title" content="{escape(title)}" />
  <meta property="og:description" content="{escape(description)}" />
  <meta property="og:url" content="{escape(canonical)}" />{og_published}
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{escape(title)}" />
  <meta name="twitter:description" content="{escape(description)}" />
  <link rel="alternate" type="application/rss+xml" title="{escape(SITE_NAME)} feed" href="/rss.xml" />
  <script type="application/ld+json">{json_ld}</script>
  <link rel="stylesheet" href="https://oat.ink/oat.min.css" />
  <script>
{THEME_BOOT_JS}  </script>
  <style>
{PAGE_CSS}  </style>"""


def render_page(
    *,
    title: str,
    description: str,
    canonical: str,
    published: str | None,
    h1: str,
    meta_line: str,
    nav_links: list[tuple[str, str]],
    json_href: str,
    archive: str,
    recap_title: str,
    recap_range: str,
    intro_html: str,
    body_html: str,
) -> str:
    nav = "".join(f'\n        <a href="{escape(h)}" role="button">{escape(t)}</a>' for h, t in nav_links)
    return f"""<!doctype html>
<html lang="en">
<head>
{render_head(title=title, description=description, canonical=canonical, published=published)}
</head>
<body>
  <main>
    <header>
      <div class="topbar">
        <h1>{h1}</h1>
        <button id="themeToggle" type="button" aria-label="Toggle theme">🌙 Dark</button>
      </div>
      <p id="meta" class="muted">{escape(meta_line)}</p>
      <menu>{nav}
        <a href="{escape(json_href)}" role="button">JSON</a>
        {archive}
      </menu>
    </header>

    <section id="recap">
      <h2 class="recap-title">{escape(recap_title)}</h2>
      <p class="recap-range">{escape(recap_range)}</p>
      {intro_html}
      {body_html}
    </section>

    <footer>
      Built from the AI SOTA feed. Each item links to its original source. ·
      <a href="/rss.xml">RSS</a>
    </footer>
  </main>
  <script>
{PAGE_JS}  </script>
</body>
</html>
"""


def load_recaps(directory: Path, file_re: re.Pattern, id_field: str) -> list[dict]:
    recaps = []
    if not directory.is_dir():
        return recaps
    for path in sorted(directory.glob("*.json")):
        if not file_re.match(path.name):
            continue
        data = load_json(path)
        if isinstance(data, dict) and data.get(id_field) and data.get("categories"):
            recaps.append(data)
    recaps.sort(key=lambda r: str(r.get(id_field)), reverse=True)
    return recaps


def meta_line_for(recap: dict) -> str:
    cats = recap.get("categories") or []
    total = recap.get("article_count") or sum(len(c.get("articles") or []) for c in cats)
    return f"{total} articles · {len(cats)} categories"


def render_daily_pages(base_url: str) -> list[str]:
    recaps = load_recaps(DAILY_DIR, DATE_FILE_RE, "date")
    out_dir = WEB_DIR / "daily"
    archive_options = [
        (f"/daily/{r['date']}", f"{r['date']} · {squeeze(r.get('title'))}") for r in recaps
    ]
    ids = []
    for recap in recaps:
        day = str(recap["date"])
        canonical = f"{base_url}/daily/{day}"
        html = render_page(
            title=squeeze(recap.get("title")) or f"AI Daily Recap — {day}",
            description=recap_description(recap),
            canonical=canonical,
            published=iso_or_none(recap.get("generated_at")),
            h1="📰 AI Daily Recap",
            meta_line=meta_line_for(recap),
            nav_links=[("/", "← Live feed"), ("/weekly", "🗓️ Weekly recap"), ("/voices", "🗣️ Voices"), ("/rss.xml", "🔔 RSS")],
            json_href=f"/api/daily?date={day}",
            archive=render_archive_select(archive_options, f"/daily/{day}", "Day"),
            recap_title=squeeze(recap.get("title")) or day,
            recap_range=fmt_long_date(day),
            intro_html=render_intro(recap),
            body_html=render_categories(recap, "daily-link"),
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{day}.html").write_text(html, encoding="utf-8")
        ids.append(day)
    prune_orphans(out_dir, DATE_HTML_RE, {f"{i}.html" for i in ids})
    return ids


def render_weekly_pages(base_url: str) -> list[str]:
    recaps = load_recaps(WEEKLY_DIR, WEEK_FILE_RE, "week")
    out_dir = WEB_DIR / "weekly"
    archive_options = [
        (f"/weekly/{r['week']}", f"{r['week']} · {squeeze(r.get('title'))}") for r in recaps
    ]
    ids = []
    for recap in recaps:
        week = str(recap["week"])
        canonical = f"{base_url}/weekly/{week}"
        recap_range = " – ".join(
            s for s in (str(recap.get("start") or ""), str(recap.get("end") or "")) if s
        )
        html = render_page(
            title=squeeze(recap.get("title")) or f"AI Weekly Recap — {week}",
            description=recap_description(recap),
            canonical=canonical,
            published=iso_or_none(recap.get("generated_at")),
            h1="🗓️ AI Weekly Recap",
            meta_line=meta_line_for(recap),
            nav_links=[("/", "← Live feed"), ("/daily", "📰 Daily recap"), ("/voices", "🗣️ Voices"), ("/rss.xml", "🔔 RSS")],
            json_href=f"/api/weekly?week={week}",
            archive=render_archive_select(archive_options, f"/weekly/{week}", "Week"),
            recap_title=squeeze(recap.get("title")) or week,
            recap_range=f"{recap_range} · {week}" if recap_range else week,
            intro_html=render_intro(recap),
            body_html=render_categories(recap, "weekly-link"),
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{week}.html").write_text(html, encoding="utf-8")
        ids.append(week)
    prune_orphans(out_dir, WEEK_HTML_RE, {f"{i}.html" for i in ids})
    return ids


def prune_orphans(out_dir: Path, html_re: re.Pattern, keep: set[str]) -> None:
    if not out_dir.is_dir():
        return
    for path in out_dir.glob("*.html"):
        if html_re.match(path.name) and path.name not in keep:
            path.unlink()
            print(f"pruned stale page: {path.relative_to(ROOT)}")


def write_sitemap(base_url: str, days: list[str], weeks: list[str]) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    entries: list[tuple[str, str | None, str | None]] = [
        (f"{base_url}/", today, "hourly"),
        (f"{base_url}/daily", today, "daily"),
        (f"{base_url}/weekly", today, "weekly"),
        (f"{base_url}/voices", None, "monthly"),
    ]
    entries += [(f"{base_url}/daily/{d}", d, None) for d in days]
    # Weekly recaps: lastmod = the week's end date when derivable.
    for w in weeks:
        entries.append((f"{base_url}/weekly/{w}", None, None))

    rows = []
    for loc, lastmod, changefreq in entries:
        parts = [f"<loc>{escape(loc)}</loc>"]
        if lastmod:
            parts.append(f"<lastmod>{escape(lastmod)}</lastmod>")
        if changefreq:
            parts.append(f"<changefreq>{escape(changefreq)}</changefreq>")
        rows.append("  <url>" + "".join(parts) + "</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    (WEB_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def write_robots(base_url: str) -> None:
    (WEB_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="public site origin for canonical/sitemap URLs")
    args = ap.parse_args()
    base_url = args.base_url.rstrip("/")

    days = render_daily_pages(base_url)
    weeks = render_weekly_pages(base_url)
    write_sitemap(base_url, days, weeks)
    write_robots(base_url)
    print(f"static pages rendered: {len(days)} daily, {len(weeks)} weekly -> web/daily/, web/weekly/")
    print(f"sitemap: web/sitemap.xml ({4 + len(days) + len(weeks)} urls), robots: web/robots.txt")
    if not days and not weeks:
        print("warning: no recaps found; nothing rendered", file=sys.stderr)


if __name__ == "__main__":
    main()
