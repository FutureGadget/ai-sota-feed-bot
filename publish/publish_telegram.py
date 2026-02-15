from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def clean(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def short_why(s: str) -> str:
    s = clean(s or "", 120)
    low = s.lower()
    if low.startswith("likely impact on ") and "platform decisions" in low:
        core = s[len("Likely impact on ") :]
        core = core.replace("workflows and platform decisions.", "").replace("and platform decisions.", "")
        core = core.strip(" .")
        if core:
            return clean(f"Impact: {core}.", 88)
    return clean(s, 88)


def type_emoji(t: str) -> str:
    m = {
        "paper": "📄",
        "release": "🛠️",
        "news": "📰",
    }
    return m.get((t or "").lower(), "📰")


def topic_emoji(it: dict) -> str:
    text = f"{it.get('title','')} {it.get('why_it_matters','')}".lower()
    if "agent" in text:
        return "🤖"
    if "inference" in text or "latency" in text:
        return "⚡"
    if "cost" in text or "token" in text:
        return "📉"
    return "💡"


def load_source_stats() -> tuple[int, int]:
    p = ROOT / "data" / "health" / "ingest_runs.jsonl"
    if not p.exists():
        return 0, 0
    rows = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue
    if not rows:
        return 0, 0

    latest_ts = rows[-1].get("ts")
    if not latest_ts:
        return 0, 0
    batch = [r for r in rows if r.get("ts") == latest_ts]
    total = len(batch)
    ok = sum(1 for r in batch if r.get("status") == "ok")
    return ok, total


def build_mobile_message(max_items: int = 12, top_n: int = 5) -> str:
    processed_file = ROOT / "data" / "processed" / "latest.json"
    if not processed_file.exists():
        digest_file = ROOT / "data" / "digest" / "latest.md"
        return digest_file.read_text(encoding="utf-8")[:3800]

    items = json.loads(processed_file.read_text(encoding="utf-8"))[:max_items]
    today = datetime.now().strftime("%Y-%m-%d")

    llm_used = sum(1 for x in items if x.get("llm_label_source") == "llm")
    src_ok, src_total = load_source_stats()
    model = os.getenv("LLM_MODEL_NAME", "claude-haiku-4-5")

    top = items[:top_n]
    rest = items[top_n:]

    lines = [f"📰 AI Feed ({today}) · {len(items)} picks", "", "🔥 Top 5"]

    for i, it in enumerate(top, start=1):
        title = clean(it.get("title", ""), 88)
        source = it.get("source", "unknown")
        url = it.get("url", "")
        why = short_why(it.get("why_it_matters") or it.get("llm_why_1line") or "")
        lines.append(f"{i}) {type_emoji(it.get('type'))}{topic_emoji(it)} {title}")
        lines.append(f"   [{source}] {url}")
        if why:
            lines.append(f"   ↳ {why}")

    if rest:
        lines.append("")
        lines.append("🧩 More")
        for i, it in enumerate(rest, start=top_n + 1):
            title = clean(it.get("title", ""), 72)
            source = it.get("source", "unknown")
            url = it.get("url", "")
            lines.append(f"{i}) {type_emoji(it.get('type'))} {title} [{source}]")
            if url:
                lines.append(f"   {url}")

    lines.append("")
    lines.append(f"📊 LLM labels: {llm_used}/{len(items)} · Sources: {src_ok}/{src_total} · {model}")
    lines.append("Feedback: useful / irrelevant / hype")

    text = "\n".join(lines)
    return text[:3900]


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    max_items = int(os.getenv("TELEGRAM_MAX_ITEMS", "12"))
    top_n = int(os.getenv("TELEGRAM_TOP_WHY", "5"))

    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    text = build_mobile_message(max_items=max_items, top_n=top_n)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    print("telegram_sent=true")


if __name__ == "__main__":
    main()
