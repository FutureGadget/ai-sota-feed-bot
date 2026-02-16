from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import feedparser
import yaml

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
        lastmod = (mod_el.text or "").strip() if mod_el is not None else now.isoformat()
        rows.append((loc, lastmod))

    rows.sort(key=lambda x: x[1], reverse=True)

    out = []
    for loc, lastmod in rows[:60]:
        out.append(
            {
                "title": prettify_slug(loc),
                "url": loc,
                "summary": "",
                "published": lastmod or now.isoformat(),
            }
        )
    return out


def run():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    out_dir = ROOT / "data" / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    all_items = []
    source_stats = []
    circuit = load_circuit_state()

    for source in load_sources():
        src_name = source["name"]
        src_type = source.get("type", "rss")
        src_url = source.get("url") or f"arxiv://{source.get('category','unknown')}"
        src_weight = float(source.get("weight", 1.0))

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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    append_ingest_run(source_stats)

    print(f"collected={len(all_items)} file={path}")
    ok = sum(1 for s in source_stats if s["status"] == "ok")
    skipped = sum(1 for s in source_stats if s["status"] == "skipped_open_circuit")
    errors = sum(1 for s in source_stats if s["status"] == "error")
    print(f"sources_ok={ok} sources_error={errors} sources_skipped={skipped} sources_total={len(source_stats)}")


if __name__ == "__main__":
    run()
