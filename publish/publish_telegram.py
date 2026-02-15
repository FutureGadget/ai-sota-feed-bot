from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def clean(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def esc(s: str, n: int = 120) -> str:
    return html.escape(clean(s, n))


def short_why(s: str) -> str:
    s = clean(s or "", 120)
    low = s.lower()
    if low.startswith("likely impact on ") and "platform decisions" in low:
        core = s[len("Likely impact on ") :]
        core = core.replace("workflows and platform decisions.", "").replace("and platform decisions.", "")
        core = core.strip(" .")
        if core:
            return clean(f"Impact: {core}.", 76)
    return clean(s, 76)


def type_emoji(t: str) -> str:
    return {"paper": "📄", "release": "🛠️", "news": "📰"}.get((t or "").lower(), "📰")


def topic_emoji(it: dict) -> str:
    text = f"{it.get('title','')} {it.get('why_it_matters','')}".lower()
    if "agent" in text:
        return "🤖"
    if "inference" in text or "latency" in text:
        return "⚡"
    if "cost" in text or "token" in text:
        return "📉"
    return "💡"


def signal_label(it: dict) -> str:
    t = (it.get("type") or "news").lower()
    src = (it.get("source") or "").lower()
    if t == "release":
        return "Tooling Release"
    if "hackernews" in src or "show hn" in (it.get("title", "").lower()):
        return "Field Report"
    if t == "paper":
        return "Research"
    return "Platform News"


def confidence_label(it: dict) -> str:
    score = float(it.get("score", 0) or 0)
    rel = float(it.get("source_reliability", 1.0) or 1.0)
    val = score + rel
    if val >= 8.0:
        return "High"
    if val >= 6.0:
        return "Medium"
    return "Low"


def action_line(it: dict) -> str:
    text = f"{it.get('title','')} {it.get('why_it_matters','')}".lower()
    if "release" in text or (it.get("type") == "release"):
        return "Check changelog + stack impact"
    if "benchmark" in text or "eval" in text:
        return "Add to eval watchlist"
    if "agent" in text:
        return "Assess for agent harness"
    if "inference" in text or "latency" in text:
        return "Review serving cost-latency"
    return "Keep in watchlist"


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
    batch = [r for r in rows if r.get("ts") == latest_ts]
    return sum(1 for r in batch if r.get("status") == "ok"), len(batch)


def build_messages(max_items: int = 12, top_n: int = 5) -> list[str]:
    processed_file = ROOT / "data" / "processed" / "latest.json"
    if not processed_file.exists():
        digest_file = ROOT / "data" / "digest" / "latest.md"
        return [digest_file.read_text(encoding="utf-8")[:3800]]

    items = json.loads(processed_file.read_text(encoding="utf-8"))[:max_items]
    today = datetime.now().strftime("%Y-%m-%d")
    top = items[:top_n]
    rest = items[top_n:]

    src_ok, src_total = load_source_stats()
    llm_used = sum(1 for x in items if x.get("llm_label_source") == "llm")
    model = os.getenv("LLM_MODEL_NAME", "claude-haiku-4-5")

    top_lines = [
        f"<b>📰 AI Feed ({today}) · {len(items)} picks</b>",
        "",
        "<b>🔥 Top 5</b>",
    ]
    for i, it in enumerate(top, start=1):
        title = esc(it.get("title", ""), 88)
        source = esc(it.get("source", "unknown"), 32)
        url = it.get("url", "")
        signal = esc(signal_label(it), 24)
        conf = esc(confidence_label(it), 12)
        why = esc(short_why(it.get("why_it_matters") or it.get("llm_why_1line") or ""), 76)
        action = esc(action_line(it), 56)

        top_lines.append(f"<b>{i}) {type_emoji(it.get('type'))}{topic_emoji(it)} <a href=\"{html.escape(url)}\">{title}</a></b>")
        top_lines.append(f"<i>{signal} · {conf}</i>")
        if why:
            top_lines.append(f"• Why: {why}")
        top_lines.append(f"• Action: {action}")
        top_lines.append(f"<code>[{source}]</code>")
        top_lines.append("")

    more_lines = ["<b>🧩 More</b>"]
    for i, it in enumerate(rest, start=top_n + 1):
        title = esc(it.get("title", ""), 70)
        source = esc(it.get("source", "unknown"), 32)
        url = it.get("url", "")
        more_lines.append(f"{i}) {type_emoji(it.get('type'))} <a href=\"{html.escape(url)}\">{title}</a> <code>[{source}]</code>")

    more_lines.append("")
    more_lines.append(f"<b>📊</b> LLM labels: <b>{llm_used}/{len(items)}</b> · Sources: <b>{src_ok}/{src_total}</b> · {esc(model,40)}")
    more_lines.append("Feedback: useful / irrelevant / hype")

    return ["\n".join(top_lines)[:3900], "\n".join(more_lines)[:3900]]


def send_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
        "parse_mode": "HTML",
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    max_items = int(os.getenv("TELEGRAM_MAX_ITEMS", "12"))
    top_n = int(os.getenv("TELEGRAM_TOP_WHY", "5"))

    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    messages = build_messages(max_items=max_items, top_n=top_n)
    for msg in messages:
        send_message(token, chat_id, msg)

    print("telegram_sent=true")


if __name__ == "__main__":
    main()
