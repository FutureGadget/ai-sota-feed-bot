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


def run():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    out_dir = ROOT / "data" / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    all_items = []
    source_stats = []
    circuit = load_circuit_state()

    for source in load_sources():
        if source.get("type") != "rss":
            continue

        src_name = source["name"]
        src_url = source["url"]
        src_weight = float(source.get("weight", 1.0))

        c = circuit.get(src_name, {})
        if c.get("state") == "open" and c.get("open_until"):
            try:
                open_until = datetime.fromisoformat(c["open_until"].replace("Z", "+00:00"))
                if open_until.tzinfo is None:
                    open_until = open_until.replace(tzinfo=timezone.utc)
            except Exception:
                open_until = now
            if open_until > now:
                source_stats.append(
                    {
                        "ts": now.isoformat(),
                        "source": src_name,
                        "url": src_url,
                        "status": "skipped_open_circuit",
                        "items": 0,
                        "open_until": c.get("open_until"),
                    }
                )
                continue

        try:
            parsed = feedparser.parse(src_url)
            entries = parsed.entries[:40]
            count = 0
            for e in entries:
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
                count += 1
                all_items.append(
                    {
                        "id": item_id(link, title),
                        "source": src_name,
                        "source_weight": src_weight,
                        "title": title,
                        "url": link,
                        "summary": summary,
                        "published": published,
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
    print(f"sources_ok={ok} sources_skipped={skipped} sources_total={len(source_stats)}")


if __name__ == "__main__":
    run()
