from __future__ import annotations

import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    digest_file = os.getenv("DIGEST_FILE", str(ROOT / "data" / "digest" / "latest.md"))

    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    text = Path(digest_file).read_text(encoding="utf-8")
    text += "\n\nFeedback format (manual):\npython pipeline/feedback.py add --url <item_url> --signal useful|irrelevant|hype"
    text = text[:3900]

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
