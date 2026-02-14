from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_sources():
    with open(ROOT / "config" / "sources.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def item_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def run():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    out_dir = ROOT / "data" / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    all_items = []
    for source in load_sources():
        if source.get("type") != "rss":
            continue

        parsed = feedparser.parse(source["url"])
        for e in parsed.entries[:40]:
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", "")
            published = (
                getattr(e, "published", None)
                or getattr(e, "updated", None)
                or now.isoformat()
            )
            if not title or not link:
                continue

            all_items.append(
                {
                    "id": item_id(link, title),
                    "source": source["name"],
                    "source_weight": float(source.get("weight", 1.0)),
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published": published,
                    "collected_at": now.isoformat(),
                }
            )

    path = out_dir / "items.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"collected={len(all_items)} file={path}")


if __name__ == "__main__":
    run()
