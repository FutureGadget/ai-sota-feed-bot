from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def build_brief_message(max_items: int = 18) -> str:
    processed_file = ROOT / "data" / "processed" / "latest.json"
    if not processed_file.exists():
        digest_file = ROOT / "data" / "digest" / "latest.md"
        return digest_file.read_text(encoding="utf-8")[:3800]

    items = json.loads(processed_file.read_text(encoding="utf-8"))[:max_items]
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [f"📰 AI Feed ({today}) — {len(items)} items", ""]
    for i, it in enumerate(items, start=1):
        title = (it.get("title") or "").strip().replace("\n", " ")
        source = it.get("source", "unknown")
        url = it.get("url", "")
        lines.append(f"{i}. {title}")
        lines.append(f"   [{source}] {url}")

    lines.append("")
    lines.append("Feedback: useful / irrelevant / hype")
    text = "\n".join(lines)
    return text[:3900]


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    max_items = int(os.getenv("TELEGRAM_MAX_ITEMS", "18"))

    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    text = build_brief_message(max_items=max_items)

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
