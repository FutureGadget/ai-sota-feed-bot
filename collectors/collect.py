from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import feedparser
import yaml
from dateutil import parser as dt_parser

ROOT = Path(__file__).resolve().parents[1]

# Optional server-side operational telemetry (pipeline/telemetry.py). Never let
# an import or capture failure break collection.
sys.path.insert(0, str(ROOT / "pipeline"))
try:
    import telemetry
except Exception:
    telemetry = None


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
        href = (href or "").strip()
        # Must be an absolute http(s) (or protocol-relative) URL. This rejects
        # placeholder/example markup scraped from article bodies — e.g. Simon
        # Willison's <click-to-play> post embeds <img src="URL to first frame">
        # as a code sample — and relative paths, both of which would otherwise
        # be rendered as <img src>/og:image and resolve against our own domain
        # and 404.
        if not re.match(r"^(?:https?:)?//\S+$", href):
            return False
        return not _is_bad_image_url(href)

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


def compile_title_excludes(source: dict) -> list[re.Pattern]:
    """Compile a source's `exclude_title_regex:` blocklist (config/sources.yaml).

    Scoped to one source, unlike `profile.selection.exclude_title_regex`, which
    is matched against every source's titles. Use it when a site-wide feed is
    the only machine-readable option and it carries a recurring non-editorial
    series (databricks_blog's "What is …" SEO glossary posts). An invalid
    pattern raises, so the source is recorded as `status: error` rather than
    silently collecting the titles it was meant to drop."""
    return [re.compile(str(p)) for p in (source.get("exclude_title_regex") or [])]


def rss_source_urls(source: dict) -> list[str]:
    """Feed URLs for an rss source. `urls:` fans several feeds into a single
    source identity (one health record, one max_per_source cap); `url:` stays
    the single-feed form. Used for tag-scoped feeds that carve an on-topic
    slice out of a broader blog and overlap each other."""
    urls = source.get("urls")
    if isinstance(urls, list):
        return [str(u).strip() for u in urls if str(u).strip()]
    single = str(source.get("url") or "").strip()
    return [single] if single else []


GNEWS_SUFFIX_SEPARATORS = (" - ", " \u2013 ", " | ")


def _publisher_fields(entry, feed_host: str) -> tuple[str, str]:
    """Google News RSS names the real outlet per entry via <source>
    (feedparser exposes entry.source as {'href': ..., 'title': ...}); plain
    feeds never set it. The href host guard skips self-referencing Google
    entries so we never label a publisher 'news.google.com'."""
    src = getattr(entry, "source", None)
    if not isinstance(src, dict):
        return "", ""
    name = str(src.get("title") or "").strip()
    href = str(src.get("href") or "").strip()
    try:
        host = (urllib.parse.urlparse(href).hostname or "") if href else ""
    except ValueError:
        host = ""
    if not name or not host or host == feed_host:
        return "", ""
    return name, host.removeprefix("www.")


def _strip_publisher_suffix(title: str, publisher_name: str, publisher_domain: str) -> str:
    """Drop a trailing '<sep> <publisher>' debris segment ('... - Bloomberg.com').

    Exact-match only against the captured publisher labels, so editorial titles
    that merely contain them stay intact."""
    def norm(s: str) -> str:
        return " ".join(s.split()).casefold()

    labels = {norm(x) for x in (publisher_name, publisher_domain) if x}
    if not labels:
        return title
    for sep in GNEWS_SUFFIX_SEPARATORS:
        idx = title.rfind(sep)
        if idx <= 0:
            continue
        if norm(title[idx + len(sep):]) in labels:
            return title[:idx].rstrip()
    return title


def collect_from_rss(source: dict, now: datetime) -> list[dict]:
    out = []
    seen: set[str] = set()
    for feed_url in rss_source_urls(source):
        parsed = feedparser.parse(feed_url)
        try:
            feed_host = urllib.parse.urlparse(feed_url).hostname or ""
        except ValueError:
            feed_host = ""
        for e in parsed.entries[:40]:
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", "")
            published = getattr(e, "published", None) or getattr(e, "updated", None) or now.isoformat()
            if not title or not link:
                continue
            # Overlapping tag feeds repeat the same post; collapse here so one
            # article is not counted several times against the source stats.
            key = link.split("?")[0].rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            publisher_name, publisher_domain = _publisher_fields(e, feed_host)
            if publisher_name or publisher_domain:
                title = _strip_publisher_suffix(title, publisher_name, publisher_domain)
            item = {
                "title": title,
                "url": link,
                "summary": summary,
                "published": published,
                "image_url": extract_image_url(e, summary),
            }
            if publisher_name:
                item["publisher_name"] = publisher_name
            if publisher_domain:
                item["publisher_domain"] = publisher_domain
            out.append(item)
    return out


# Quantization/format re-uploads shipped alongside a main model drop
# (…-FP8, …-GGUF, …-Int4, HF-format conversions). Collapsed so one launch
# yields one feed item instead of one per artifact flavor.
HF_VARIANT_SUFFIX_RE = re.compile(
    r"(?:[-_](?:fp8|fp16|bf16|mxfp8|mxfp4|int4|int8|gptq|awq|gguf|mlx|hf))+$",
    re.IGNORECASE,
)


def hf_models_to_entries(models: list[dict], org: str, now: datetime) -> list[dict]:
    """Pure mapping from a Hugging Face /api/models org listing (newest-first)
    to collector entries, collapsing quantized/format variants onto the
    canonical repo (preferring the unsuffixed name, then the most-liked)."""
    groups: dict[str, dict] = {}
    order: list[str] = []
    for m in models:
        if not isinstance(m, dict) or m.get("private"):
            continue
        mid = str(m.get("id") or m.get("modelId") or "").strip()
        if not mid or "/" not in mid:
            continue
        name = mid.split("/", 1)[1]
        base = HF_VARIANT_SUFFIX_RE.sub("", name).lower()
        cur = groups.get(base)
        if cur is None:
            groups[base] = m
            order.append(base)
            continue
        cur_name = str(cur.get("id", "")).split("/", 1)[-1]
        cur_canonical = HF_VARIANT_SUFFIX_RE.sub("", cur_name) == cur_name
        new_canonical = HF_VARIANT_SUFFIX_RE.sub("", name) == name
        if (new_canonical and not cur_canonical) or (
            new_canonical == cur_canonical
            and int(m.get("likes") or 0) > int(cur.get("likes") or 0)
        ):
            groups[base] = m
    out = []
    for base in order:
        m = groups[base]
        mid = str(m.get("id") or m.get("modelId") or "").strip()
        created = str(m.get("createdAt") or "").strip() or now.isoformat()
        parts = [f"New model weights from {org} on Hugging Face."]
        tag = str(m.get("pipeline_tag") or "").strip()
        if tag:
            parts.append(f"Task: {tag}.")
        likes = m.get("likes")
        downloads = m.get("downloads")
        if likes is not None or downloads is not None:
            parts.append(f"Likes: {likes or 0}, downloads: {downloads or 0}.")
        out.append(
            {
                "title": f"{mid} released on Hugging Face",
                "url": f"https://huggingface.co/{mid}",
                "summary": " ".join(parts),
                "published": created,
                "image_url": "",
            }
        )
    return out


def collect_from_hf_org(source: dict, now: datetime) -> list[dict]:
    """First-party model-drop signal for open-weight labs: the Hugging Face
    Hub org listing. For these labs the weights landing on HF *is* the launch
    (it precedes their blog posts and any press coverage), and none of them
    exposes a working RSS/sitemap (see config/sources.yaml comments and the
    2026-07-17 decision-log entries)."""
    org = str(source.get("org") or "").strip()
    if not org:
        raise ValueError("hf_org_models source requires org")
    max_results = int(source.get("max_results", 10))
    url = (
        "https://huggingface.co/api/models?author="
        + urllib.parse.quote(org)
        + f"&sort=createdAt&direction=-1&limit={max_results}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "ai-sota-feed-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        models = json.loads(resp.read().decode("utf-8"))
    if not isinstance(models, list):
        raise ValueError("hf_org_models: unexpected API response shape")
    return hf_models_to_entries(models, org, now)


def collect_from_arxiv_api(source: dict, now: datetime) -> list[dict]:
    # Two query modes: a plain category dump (`category: cs.CL` -> `cat:cs.CL`)
    # or a raw arXiv `search_query` for topic-targeted recall across categories
    # (e.g. '(cat:cs.CL OR cat:cs.AI) AND (abs:hallucination OR abs:factuality)').
    # search_query widens the catch beyond the per-category latest-N window;
    # overlap with category sources is harmless — downstream dedupe() collapses
    # by canonical arXiv URL before ranking.
    search_query = (source.get("search_query") or "").strip()
    category = source.get("category")
    if not search_query and not category:
        raise ValueError("arxiv_api source requires search_query or category")
    max_results = int(source.get("max_results", 40))
    raw_query = search_query if search_query else f"cat:{category}"
    q = urllib.parse.quote(raw_query)
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


OPENREVIEW_API_BASE = "https://api2.openreview.net"


def _openreview_content_value(value) -> str:
    """Extract an API v2 content value, which may be wrapped or scalar."""
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None)
    return str(value).strip()


def _openreview_timestamp(value) -> str | None:
    """Normalize an OpenReview date, accepting API milliseconds or ISO text."""
    if value is None or value == "":
        return None
    try:
        numeric = isinstance(value, (int, float)) or re.fullmatch(
            r"\d+(?:\.\d+)?", str(value).strip()
        )
        if numeric:
            epoch = float(value)
            if epoch > 10_000_000_000:
                epoch /= 1000.0
            return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
        parsed = dt_parser.parse(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (OverflowError, TypeError, ValueError, OSError):
        return None


def _openreview_note_value(note: dict, field: str) -> str:
    return _openreview_content_value((note.get("content") or {}).get(field))


def _openreview_note_timestamp(note: dict, field: str) -> str | None:
    """Read a timestamp from a top-level or content field."""
    return _openreview_timestamp(note.get(field) or _openreview_note_value(note, field))


def _openreview_replies(note: dict) -> list[dict]:
    details = note.get("details") or {}
    replies = details.get("directReplies") or details.get("replies") or []
    if isinstance(replies, dict):
        replies = replies.get("notes") or []
    return [reply for reply in replies if isinstance(reply, dict)]


def _openreview_decision(reply: dict) -> str:
    invitation = str(reply.get("invitation") or "").casefold()
    content = reply.get("content") or {}
    decision = _openreview_content_value(content.get("decision"))
    if decision and ("decision" in invitation or "decision" in content):
        return decision
    return ""


def _openreview_decision_candidates(note: dict) -> list[tuple[str, dict, str]]:
    candidates = []
    for reply in _openreview_replies(note):
        decision = _openreview_decision(reply)
        if not decision:
            continue
        timestamp = _openreview_timestamp(
            reply.get("tcdate")
            or reply.get("tmdate")
            or reply.get("cdate")
            or reply.get("mdate")
        )
        candidates.append((timestamp or "", reply, decision))
    return candidates


def _openreview_is_withdrawn(note: dict) -> bool:
    values = (
        _openreview_note_value(note, "venue"),
        _openreview_note_value(note, "venueid"),
        _openreview_note_value(note, "status"),
    )
    return any("withdraw" in value.casefold() for value in values)


def _openreview_is_accepted(decision: str) -> bool:
    normalized = re.sub(r"\s+", " ", decision).strip().casefold()
    return normalized.startswith("accept") and "reject" not in normalized


def _openreview_request_notes(params: dict[str, str | int]) -> dict:
    query = urllib.parse.urlencode(params)
    url = f"{OPENREVIEW_API_BASE}/notes?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-sota-feed-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("notes"), list):
        raise ValueError("openreview_venue: unexpected API response shape")
    return payload


def collect_from_openreview_venue(source: dict, now: datetime) -> list[dict]:
    """Collect public submissions from an OpenReview API v2 venue."""
    venue_id = str(source.get("venue_id") or "").strip().strip("/")
    if not venue_id:
        raise ValueError("openreview_venue source requires venue_id")

    accepted_only = source.get("accepted_only", True)
    if isinstance(accepted_only, str):
        accepted_only = accepted_only.strip().casefold() not in {"0", "false", "no"}
    accepted_only = bool(accepted_only)
    max_results = max(1, int(source.get("max_results", 100)))
    page_size = max(1, min(int(source.get("page_size", 100)), max_results))
    submission_invitation = f"{venue_id}/-/Submission"
    offset = 0
    fetched = 0
    out = []
    skipped = {
        "not_accepted": 0,
        "withdrawn": 0,
        "anonymous": 0,
        "missing_decision": 0,
        "missing_timestamp": 0,
        "missing_metadata": 0,
    }

    while len(out) < max_results:
        payload = _openreview_request_notes(
            {
                "invitation": submission_invitation,
                "details": "directReplies",
                "sort": "tmdate:desc",
                "limit": page_size,
                "offset": offset,
                "count": "true",
            }
        )
        notes = payload["notes"]
        if not notes:
            break
        fetched += len(notes)

        for note in notes:
            title = _openreview_note_value(note, "title")
            abstract = _openreview_note_value(note, "abstract")
            forum = str(note.get("forum") or "").strip()
            if not title or not forum:
                skipped["anonymous" if not forum else "missing_metadata"] += 1
                continue
            if _openreview_is_withdrawn(note):
                skipped["withdrawn"] += 1
                continue

            decision_reply = None
            decision = ""
            if accepted_only:
                # OpenReview's documented accepted-paper path is content.venueid
                # == the venue ID. Public responses may also include a Decision
                # reply, so use it as a consistency check and timestamp fallback.
                venue_id_value = _openreview_note_value(note, "venueid")
                decision_candidates = _openreview_decision_candidates(note)
                timestamped_decisions = [row for row in decision_candidates if row[0]]
                if timestamped_decisions:
                    _, decision_reply, decision = max(
                        timestamped_decisions, key=lambda row: row[0]
                    )
                elif decision_candidates:
                    _, decision_reply, decision = decision_candidates[-1]

                if venue_id_value:
                    accepted = venue_id_value.strip().rstrip("/") == venue_id
                    if decision and not _openreview_is_accepted(decision):
                        accepted = False
                elif decision:
                    accepted = _openreview_is_accepted(decision)
                else:
                    accepted = False

                if not accepted:
                    if venue_id_value or decision:
                        skipped["not_accepted"] += 1
                    else:
                        skipped["missing_decision"] += 1
                    continue

                published = _openreview_note_timestamp(note, "pdate")
                if not published and decision_reply:
                    published = _openreview_timestamp(
                        decision_reply.get("tcdate")
                        or decision_reply.get("tmdate")
                        or decision_reply.get("cdate")
                        or decision_reply.get("mdate")
                    )
            else:
                published = _openreview_timestamp(
                    note.get("tcdate")
                    or note.get("tmdate")
                    or note.get("cdate")
                    or note.get("mdate")
                )
            if not published:
                skipped["missing_timestamp"] += 1
                continue

            out.append(
                {
                    "title": title,
                    "url": "https://openreview.net/forum?id=" + urllib.parse.quote(forum, safe=""),
                    "summary": re.sub(r"\s+", " ", abstract).strip(),
                    "published": published,
                }
            )
            if len(out) >= max_results:
                break

        if len(notes) < page_size:
            break
        offset += len(notes)
        try:
            total = int(payload.get("count"))
        except (TypeError, ValueError):
            total = None
        if total is not None and offset >= total:
            break

    skip_bits = " ".join(f"{key}={value}" for key, value in skipped.items() if value)
    print(
        f"openreview_venue venue={venue_id} fetched={fetched} accepted={len(out)}"
        + (f" {skip_bits}" if skip_bits else "")
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


def _sitemap_meta_cache_row(meta: dict, previous: dict, now: datetime) -> dict:
    """Build a cache row while keeping the URL's first discovery time stable."""
    discovered_at = (
        previous.get("discovered_at")
        or previous.get("fetched_at")
        or now.isoformat()
    )
    published = meta.get("published")
    return {
        "published": published,
        # Presence of this field marks a completed lookup. Older null rows lack
        # it and are refreshed once when the parser learns a new page format.
        "published_missing": published is None,
        "title": meta.get("title"),
        "description": meta.get("description"),
        "discovered_at": discovered_at,
        "fetched_at": now.isoformat(),
    }


def _extract_published_from_html(html_text: str) -> str | None:
    patterns = [
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'publishedOn\\*"\\*:\\*\\*"(\d{4}-\d{2}-\d{2}(?:T[\d:.]+Z?)?)',
        # Anthropic's current article shell renders the real date as the plain
        # text sibling immediately after its PostDetail heading. Keep this
        # scoped to that structure so unrelated dates in the body/footer cannot
        # be mistaken for publication metadata.
        r'<h1[^>]+class=["\'][^"\']*PostDetail[^"\']*["\'][^>]*>[\s\S]*?</h1>\s*'
        r'<div[^>]+class=["\'][^"\']*\bagate\b[^"\']*["\'][^>]*>\s*([^<]+?)\s*</div>',
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
        normalized = _normalize_published(raw)
        if normalized:
            return normalized
    return None


def _unescape_html(text: str) -> str:
    return " ".join(html.unescape(text).split())


class _PageMetadataParser(HTMLParser):
    """Collect metadata without depending on HTML attribute order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.time_values: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = {str(k).lower(): str(v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "meta":
            key = (attrs_by_name.get("property") or attrs_by_name.get("name") or "").lower()
            content = attrs_by_name.get("content", "").strip()
            if key and content and key not in self.meta:
                self.meta[key] = content
        elif tag == "time":
            value = attrs_by_name.get("datetime", "").strip()
            if value:
                self.time_values.append(value)
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)


def _parse_page_metadata(html_text: str) -> _PageMetadataParser:
    parser = _PageMetadataParser()
    parser.feed(html_text)
    parser.close()
    return parser


def _extract_title_from_metadata(meta: _PageMetadataParser) -> str | None:
    """Real page title, preferring social metadata over the title element."""
    for value in (
        meta.meta.get("og:title"),
        meta.meta.get("twitter:title"),
        " ".join(meta.title_parts),
    ):
        title = _unescape_html(value or "")
        if title:
            return title
    return None


def _extract_description_from_metadata(meta: _PageMetadataParser) -> str | None:
    """Short page summary from social or standard description metadata."""
    for key in ("og:description", "description", "twitter:description"):
        description = _unescape_html(meta.meta.get(key, ""))
        if description:
            return description
    return None


def _extract_published_from_metadata(meta: _PageMetadataParser) -> str | None:
    for key in (
        "article:published_time",
        "og:published_time",
        "publish_date",
        "date",
    ):
        raw = meta.meta.get(key)
        if raw:
            published = _normalize_published(raw)
            if published:
                return published
    for raw in meta.time_values:
        published = _normalize_published(raw)
        if published:
            return published
    return None


def _normalize_published(raw: str) -> str | None:
    try:
        dt = dt_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Date-only metadata has no trustworthy time of day. Anchor it at the
        # midpoint of the publication day so a fresh article is not treated as
        # stale for up to 24 hours by downstream freshness scoring.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw.strip()):
            dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _fetch_page_meta(url: str) -> dict:
    """Fetch a page once and pull title, description, and published date.

    Sitemaps carry only <loc>/<lastmod>, so without this the item title is a
    title-cased URL slug and the summary is empty (see collect_from_sitemap).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html_text = r.read().decode("utf-8", errors="ignore")
    page_meta = _parse_page_metadata(html_text)
    return {
        "title": _extract_title_from_metadata(page_meta),
        "description": _extract_description_from_metadata(page_meta),
        "published": _extract_published_from_html(html_text)
        or _extract_published_from_metadata(page_meta),
    }


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

    # Some sitemaps (e.g. LangChain) ship no <lastmod>, so the only ordering the
    # sitemap gives is alphabetical-by-slug — meaningless for "newest". Capping
    # that order to 60 permanently hides any post whose slug sorts past the cut
    # (a brand-new "the-art-of-..." can never beat "a-..."/"b-..." entries). When
    # a sitemap carries no usable lastmod, discover the real publish dates first,
    # then keep the newest 60. Publish dates never change, so they are cached
    # forever; only a bounded number of new (uncached) pages are fetched per run,
    # so a cold cache warms up over a few runs instead of stalling one.
    if extract_from_page and not any(lm for _, lm in rows):
        budget = int(
            os.getenv(
                "COLLECT_SITEMAP_META_BUDGET",
                str(source.get("page_meta_fetch_budget", 200)),
            )
        )
        fetched = 0
        dated: list[tuple[str, str]] = []
        for loc, lastmod in rows:
            cache_row = cache.get(loc) if isinstance(cache.get(loc), dict) else None
            lookup_complete = cache_row and (
                cache_row.get("published") is not None
                or "published_missing" in cache_row
            )
            if lookup_complete:
                dated.append(
                    (
                        loc,
                        cache_row.get("published")
                        or cache_row.get("discovered_at")
                        or cache_row.get("fetched_at")
                        or now.isoformat(),
                    )
                )
                continue
            if fetched >= budget:
                continue  # out of budget this run; discovered on a later run
            try:
                meta = _fetch_page_meta(loc)
                cache[loc] = _sitemap_meta_cache_row(meta, cache_row or {}, now)
                fetched += 1
                dated.append(
                    (
                        loc,
                        cache[loc].get("published")
                        or cache[loc]["discovered_at"],
                    )
                )
            except Exception:
                continue  # transient fetch failure; retry on a later run
        # Reorder by real publish date so the [:60] cap below keeps the newest.
        dated.sort(key=lambda x: x[1], reverse=True)
        rows = [(loc, "") for loc, _ in dated]
        _save_sitemap_meta_cache(cache)

    out = []
    for loc, lastmod in rows[:60]:
        published = None
        page_title = None
        page_desc = None
        discovered_at = None

        if extract_from_page:
            cache_row = cache.get(loc, {}) if isinstance(cache.get(loc), dict) else {}
            discovered_at = (
                cache_row.get("discovered_at")
                or cache_row.get("fetched_at")
            )
            cached_at = cache_row.get("fetched_at")
            cache_ok = False
            # A cache row counts as fresh only once it carries the page meta we
            # now extract and records whether the publication lookup completed,
            # so older null-date rows are re-fetched once.
            lookup_complete = (
                cache_row.get("published") is not None
                or "published_missing" in cache_row
            )
            if cached_at and "title" in cache_row and lookup_complete:
                try:
                    fetched_dt = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                    if fetched_dt.tzinfo is None:
                        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
                    age_h = (now - fetched_dt).total_seconds() / 3600.0
                    cache_ok = age_h <= max(1, cache_ttl_hours)
                except Exception:
                    cache_ok = False
            if cache_ok:
                published = cache_row.get("published")
                page_title = cache_row.get("title")
                page_desc = cache_row.get("description")
            else:
                try:
                    meta = _fetch_page_meta(loc)
                    cache[loc] = _sitemap_meta_cache_row(meta, cache_row, now)
                    published = cache[loc].get("published")
                    page_title = cache[loc].get("title")
                    page_desc = cache[loc].get("description")
                    discovered_at = cache[loc]["discovered_at"]
                except Exception:
                    published = None
                    discovered_at = discovered_at or now.isoformat()
                    # Persist discovery separately from fetch freshness so a
                    # transient page failure cannot make this URL "new" again
                    # on every run. The missing lookup marker keeps retries on.
                    cache[loc] = {**cache_row, "discovered_at": discovered_at}

        # `<lastmod>` means the URL changed, not that it was first published.
        # Extract-enabled sources therefore fall back to their stable discovery
        # time; only plain sitemap sources retain the historical lastmod fallback.
        published = published or (
            discovered_at if extract_from_page else lastmod
        ) or now.isoformat()

        out.append(
            {
                # Real page title/summary when the fetch succeeded; the slug is
                # only a last-resort fallback (it title-cases to e.g.
                # "Dxc Anthropic Alliance" and duplicates into summary_1line).
                "title": (page_title or "").strip() or prettify_slug(loc),
                "url": loc,
                "summary": (page_desc or "").strip(),
                "published": published,
            }
        )

    if extract_from_page:
        _save_sitemap_meta_cache(cache)

    return out


def run():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    ingest_batch_id = now.strftime("%Y%m%d-%H%M%S")
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
        src_url = (
            source.get("url")
            or (", ".join(rss_source_urls(source)) if src_type == "rss" else "")
            or (
                f"hf://{source.get('org','unknown')}"
                if src_type == "hf_org_models"
                else (
                    f"openreview://{source.get('venue_id','unknown')}"
                    if src_type == "openreview_venue"
                    else f"arxiv://{source.get('category','unknown')}"
                )
            )
        )

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
            elif src_type == "openreview_venue":
                entries = collect_from_openreview_venue(source, now)
            elif src_type == "sitemap":
                entries = collect_from_sitemap(source, now)
            elif src_type == "hf_org_models":
                entries = collect_from_hf_org(source, now)
            else:
                raise ValueError(f"unsupported_source_type:{src_type}")

            title_excludes = compile_title_excludes(source)
            count = 0
            excluded = 0
            for ent in entries:
                title = ent["title"].strip()
                link = ent["url"].strip()
                if not title or not link:
                    continue
                if any(pat.search(title) for pat in title_excludes):
                    excluded += 1
                    continue
                count += 1
                row = {
                    "id": item_id(link, title),
                    "source": src_name,
                    "title": title,
                    "url": link,
                    "summary": ent.get("summary", ""),
                    "image_url": ent.get("image_url", ""),
                    "published": ent.get("published", now.isoformat()),
                    "collected_at": now.isoformat(),
                    "ingest_batch_id": ingest_batch_id,
                }
                for field in ("publisher_name", "publisher_domain"):
                    if ent.get(field):
                        row[field] = ent[field]
                all_items.append(row)

            stat = {
                "ts": now.isoformat(),
                "source": src_name,
                "url": src_url,
                "status": "ok",
                "items": count,
            }
            if excluded:
                stat["excluded_title"] = excluded
            source_stats.append(stat)
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

    if telemetry is not None:
        events = [
            (
                "collect_run_completed",
                {
                    "items_collected": len(all_items),
                    "sources_ok": ok,
                    "sources_error": errors,
                    "sources_skipped": skipped,
                    "sources_total": len(source_stats),
                    "ingest_batch_id": ingest_batch_id,
                    "wrote_new": wrote_new,
                },
            )
        ]
        for s in source_stats:
            if s.get("status") == "error":
                events.append(
                    (
                        "collect_source_failed",
                        {
                            "source": s.get("source"),
                            "url": s.get("url"),
                            "error": s.get("error"),
                        },
                    )
                )
        telemetry.capture_batch(events)


if __name__ == "__main__":
    run()
