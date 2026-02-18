from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import feedparser
import yaml
from dateutil import parser as dt_parser

ROOT = Path(__file__).resolve().parents[1]


def load_sources():
    with open(ROOT / "config" / "sources.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def item_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def load_circuit_state() -> dict:
    p = ROOT / "data" / "health" / "circuit_breaker.json"
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload.get("sources", {})


def append_ingest_run(stats: list[dict]) -> None:
    health_dir = ROOT / "data" / "health"
    health_dir.mkdir(parents=True, exist_ok=True)
    run_file = health_dir / "ingest_runs.jsonl"
    with open(run_file, "a", encoding="utf-8") as f:
        for row in stats:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_last_success_ts_by_source() -> dict[str, datetime]:
    p = ROOT / "data" / "health" / "ingest_runs.jsonl"
    out: dict[str, datetime] = {}
    if not p.exists():
        return out
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        return out
    for ln in lines:
        try:
            row = json.loads(ln)
        except Exception:
            continue
        if row.get("status") != "ok":
            continue
        src = row.get("source")
        ts = row.get("ts")
        if not src or not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        prev = out.get(src)
        if prev is None or dt > prev:
            out[src] = dt
    return out


def is_open_circuit(circuit: dict, src_name: str, now: datetime) -> tuple[bool, str | None]:
    c = circuit.get(src_name, {})
    if c.get("state") == "open" and c.get("open_until"):
        try:
            open_until = datetime.fromisoformat(c["open_until"].replace("Z", "+00:00"))
            if open_until.tzinfo is None:
                open_until = open_until.replace(tzinfo=timezone.utc)
        except Exception:
            open_until = now
        if open_until > now:
            return True, c.get("open_until")
    return False, None


def prettify_slug(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    slug = unquote(slug)
    slug = re.sub(r"[-_]+", " ", slug)
    return slug.strip().title() or url


def _is_bad_image_url(url: str) -> bool:
    u = (url or "").lower()
    # common avatar/profile images that look wrong in article cards
    bad_markers = [
        "avatars.githubusercontent.com",
        "gravatar.com/avatar",
        "/avatar/",
        "profile_images",
    ]
    return any(m in u for m in bad_markers)


def extract_image_url(entry, summary_html: str = "") -> str:
    def ok(href: str) -> bool:
        return bool(href) and not _is_bad_image_url(href)

    # 1) RSS enclosure
    encs = getattr(entry, "enclosures", []) or []
    for e in encs:
        href = (e.get("href") or e.get("url") or "").strip() if isinstance(e, dict) else ""
        etype = (e.get("type") or "").lower() if isinstance(e, dict) else ""
        if ok(href) and (etype.startswith("image/") or re.search(r"\.(png|jpe?g|gif|webp|avif)(\?|$)", href, re.I)):
            return href

    # 2) media RSS
    media = getattr(entry, "media_content", []) or []
    for m in media:
        href = (m.get("url") or "").strip() if isinstance(m, dict) else ""
        if ok(href):
            return href

    thumbs = getattr(entry, "media_thumbnail", []) or []
    for m in thumbs:
        href = (m.get("url") or "").strip() if isinstance(m, dict) else ""
        if ok(href):
            return href

    # 3) first image in summary/content
    body = html.unescape(summary_html or "")
    m = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", body, re.I)
    if m:
        href = m.group(1).strip()
        if ok(href):
            return href

    return ""


def collect_from_rss(source: dict, now: datetime) -> list[dict]:
    parsed = feedparser.parse(source["url"])
    out = []
    for e in parsed.entries[:40]:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        summary = getattr(e, "summary", "")
        published = getattr(e, "published", None) or getattr(e, "updated", None) or now.isoformat()
        if not title or not link:
            continue
        out.append(
            {
                "title": title,
                "url": link,
                "summary": summary,
                "published": published,
                "image_url": extract_image_url(e, summary),
            }
        )
    return out


def collect_from_arxiv_api(source: dict, now: datetime) -> list[dict]:
    category = source.get("category")
    if not category:
        raise ValueError("arxiv_api source requires category")
    max_results = int(source.get("max_results", 40))
    q = urllib.parse.quote(f"cat:{category}")
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={q}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    parsed = feedparser.parse(url)
    out = []
    for e in parsed.entries:
        title = getattr(e, "title", "").strip().replace("\n", " ")
        link = getattr(e, "id", "").strip() or getattr(e, "link", "").strip()
        summary = getattr(e, "summary", "")
        published = getattr(e, "published", None) or getattr(e, "updated", None) or now.isoformat()
        if not title or not link:
            continue
        out.append(
            {
                "title": title,
                "url": link,
                "summary": summary,
                "published": published,
            }
        )
    return out


def _load_sitemap_meta_cache() -> dict[str, dict]:
    p = ROOT / "data" / "cache" / "sitemap_meta.json"
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_sitemap_meta_cache(cache: dict[str, dict]) -> None:
    p = ROOT / "data" / "cache" / "sitemap_meta.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_published_from_html(html_text: str) -> str | None:
    patterns = [
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']publish_date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<time[^>]+datetime=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html_text, re.I)
        if not m:
            continue
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        try:
            dt = dt_parser.parse(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            continue
    return None


def _fetch_page_published(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html_text = r.read().decode("utf-8", errors="ignore")
    return _extract_published_from_html(html_text)


def collect_from_sitemap(source: dict, now: datetime) -> list[dict]:
    req = urllib.request.Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml_bytes = r.read()

    root = ET.fromstring(xml_bytes)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    include_prefixes = source.get("include_prefixes", [])
    rows = []
    for u in root.findall("sm:url", ns):
        loc_el = u.find("sm:loc", ns)
        mod_el = u.find("sm:lastmod", ns)
        if loc_el is None or not (loc_el.text or "").strip():
            continue
        loc = (loc_el.text or "").strip()
        if include_prefixes and not any(loc.startswith(p) for p in include_prefixes):
            continue
        lastmod = (mod_el.text or "").strip() if mod_el is not None else ""
        rows.append((loc, lastmod))

    rows.sort(key=lambda x: x[1], reverse=True)

    source_name = source.get("name", "")
    extract_from_page = bool(source.get("extract_published_from_page", False) or source_name == "claude_blog")
    cache_ttl_hours = int(source.get("page_meta_cache_ttl_hours", 24))
    cache = _load_sitemap_meta_cache() if extract_from_page else {}

    out = []
    for loc, lastmod in rows[:60]:
        published = None

        if extract_from_page:
            cache_row = cache.get(loc, {})
            cache_ok = False
            cached_published = cache_row.get("published") if isinstance(cache_row, dict) else None
            cached_at = cache_row.get("fetched_at") if isinstance(cache_row, dict) else None
            if cached_published and cached_at:
                try:
                    fetched_dt = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                    if fetched_dt.tzinfo is None:
                        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
                    age_h = (now - fetched_dt).total_seconds() / 3600.0
                    cache_ok = age_h <= max(1, cache_ttl_hours)
                except Exception:
                    cache_ok = False
            if cache_ok:
                published = cached_published
            else:
                try:
                    published = _fetch_page_published(loc)
                    cache[loc] = {
                        "published": published,
                        "fetched_at": now.isoformat(),
                    }
                except Exception:
                    published = None

        published = published or lastmod or now.isoformat()

        out.append(
            {
                "title": prettify_slug(loc),
                "url": loc,
                "summary": "",
                "published": published,
            }
        )

    if extract_from_page:
        _save_sitemap_meta_cache(cache)

    return out


def run():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    out_dir = ROOT / "data" / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    all_items = []
    source_stats = []
    circuit = load_circuit_state()
    last_success = load_last_success_ts_by_source()
    bypass_cooldown = str(os.getenv("COLLECT_BYPASS_COOLDOWN", "0")).strip() in {"1", "true", "yes"}

    for source in load_sources():
        src_name = source["name"]
        src_type = source.get("type", "rss")
        src_url = source.get("url") or f"arxiv://{source.get('category','unknown')}"
        src_weight = float(source.get("weight", 1.0))

        if not bypass_cooldown:
            default_poll_mins = int(os.getenv("COLLECT_DEFAULT_POLL_MINUTES", "0") or 0)
            poll_mins = int(source.get("poll_interval_minutes", default_poll_mins) or 0)
            if poll_mins > 0:
                last_dt = last_success.get(src_name)
                if last_dt is not None:
                    age_mins = (now - last_dt).total_seconds() / 60.0
                    if age_mins < poll_mins:
                        source_stats.append(
                            {
                                "ts": now.isoformat(),
                                "source": src_name,
                                "url": src_url,
                                "status": "skipped_cooldown",
                                "items": 0,
                                "cooldown_minutes": poll_mins,
                                "last_success_ts": last_dt.isoformat(),
                            }
                        )
                        continue

        blocked, open_until = is_open_circuit(circuit, src_name, now)
        if blocked:
            source_stats.append(
                {
                    "ts": now.isoformat(),
                    "source": src_name,
                    "url": src_url,
                    "status": "skipped_open_circuit",
                    "items": 0,
                    "open_until": open_until,
                }
            )
            continue

        try:
            if src_type == "rss":
                entries = collect_from_rss(source, now)
            elif src_type == "arxiv_api":
                entries = collect_from_arxiv_api(source, now)
            elif src_type == "sitemap":
                entries = collect_from_sitemap(source, now)
            else:
                raise ValueError(f"unsupported_source_type:{src_type}")

            count = 0
            for ent in entries:
                title = ent["title"].strip()
                link = ent["url"].strip()
                if not title or not link:
                    continue
                count += 1
                all_items.append(
                    {
                        "id": item_id(link, title),
                        "source": src_name,
                        "source_weight": src_weight,
                        "title": title,
                        "url": link,
                        "summary": ent.get("summary", ""),
                        "image_url": ent.get("image_url", ""),
                        "published": ent.get("published", now.isoformat()),
                        "collected_at": now.isoformat(),
                    }
                )

            source_stats.append(
                {
                    "ts": now.isoformat(),
                    "source": src_name,
                    "url": src_url,
                    "status": "ok",
                    "items": count,
                }
            )
        except Exception as e:
            source_stats.append(
                {
                    "ts": now.isoformat(),
                    "source": src_name,
                    "url": src_url,
                    "status": "error",
                    "items": 0,
                    "error": str(e),
                }
            )

    path = out_dir / "items.json"
    wrote_new = True
    if all_items:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
    else:
        wrote_new = False
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    append_ingest_run(source_stats)

    if wrote_new:
        print(f"collected={len(all_items)} file={path}")
    else:
        prev_count = 0
        try:
            prev_count = len(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            prev_count = 0
        print(f"collected=0 file={path} reuse_previous=true previous_items={prev_count}")
    ok = sum(1 for s in source_stats if s["status"] == "ok")
    skipped = sum(1 for s in source_stats if str(s.get("status", "")).startswith("skipped_"))
    errors = sum(1 for s in source_stats if s["status"] == "error")
    print(f"sources_ok={ok} sources_error={errors} sources_skipped={skipped} sources_total={len(source_stats)}")


if __name__ == "__main__":
    run()
