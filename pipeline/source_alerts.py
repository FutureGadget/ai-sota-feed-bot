from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT_FILE = ROOT / "data" / "health" / "circuit_breaker.json"
ALERTS_STATE_FILE = ROOT / "data" / "health" / "alerts_state.json"
ALERTS_OUT_FILE = ROOT / "data" / "health" / "latest_alerts.json"

OPEN_TOO_LONG_HOURS = 12
REPEAT_ALERT_COOLDOWN_HOURS = 12
SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path, default: dict):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_alerts() -> tuple[list[dict], dict]:
    circuit = load_json(CIRCUIT_FILE, {"sources": {}})
    state = load_json(ALERTS_STATE_FILE, {"sources": {}})

    alerts = []
    tnow = now_utc()
    next_state = {"generated_at": tnow.isoformat(), "sources": {}}

    for src, row in circuit.get("sources", {}).items():
        cur_state = row.get("state", "closed")
        open_until = parse_ts(row.get("open_until"))
        prev = state.get("sources", {}).get(src, {})
        prev_state = prev.get("last_state", "closed")
        last_alerted = parse_ts(prev.get("last_alerted_at"))

        source_entry = {
            "last_state": cur_state,
            "last_open_until": row.get("open_until"),
            "last_alerted_at": prev.get("last_alerted_at"),
        }

        if cur_state == "open" and prev_state != "open":
            alerts.append(
                {
                    "kind": "opened_now",
                    "severity": "critical",
                    "source": src,
                    "open_until": row.get("open_until"),
                    "reason": row.get("reason"),
                }
            )
            source_entry["last_alerted_at"] = tnow.isoformat()

        elif cur_state == "open" and open_until is not None:
            long_open = (open_until - tnow).total_seconds() / 3600.0 > OPEN_TOO_LONG_HOURS
            cooldown_ok = (
                last_alerted is None
                or (tnow - last_alerted).total_seconds() / 3600.0 >= REPEAT_ALERT_COOLDOWN_HOURS
            )
            if long_open and cooldown_ok:
                alerts.append(
                    {
                        "kind": "still_open_too_long",
                        "severity": "warning",
                        "source": src,
                        "open_until": row.get("open_until"),
                        "reason": row.get("reason"),
                    }
                )
                source_entry["last_alerted_at"] = tnow.isoformat()

        next_state["sources"][src] = source_entry

    return alerts, next_state


def filter_alerts_by_min_severity(alerts: list[dict], min_severity: str) -> list[dict]:
    threshold = SEVERITY_ORDER.get(min_severity, SEVERITY_ORDER["critical"])
    return [a for a in alerts if SEVERITY_ORDER.get(a.get("severity", "info"), 0) >= threshold]


def format_alert_text(alerts: list[dict]) -> str:
    lines = ["⚠️ AI Feed Source Alert"]
    for a in alerts:
        lines.append(
            f"- [{a.get('severity','info')}/{a['kind']}] {a['source']} (reason={a.get('reason')}, open_until={a.get('open_until')})"
        )
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("alerts_telegram_skipped=missing_secrets")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    print("alerts_telegram_sent=true")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send-telegram", action="store_true")
    ap.add_argument("--telegram-min-severity", default="critical", choices=["info", "warning", "critical"])
    args = ap.parse_args()

    alerts, next_state = build_alerts()
    save_json(ALERTS_STATE_FILE, next_state)
    save_json(
        ALERTS_OUT_FILE,
        {"generated_at": now_utc().isoformat(), "count": len(alerts), "alerts": alerts},
    )

    print(f"alerts_count={len(alerts)}")
    if alerts:
        text = format_alert_text(alerts)
        print(text)

    if args.send_telegram:
        to_send = filter_alerts_by_min_severity(alerts, args.telegram_min_severity)
        print(f"alerts_telegram_candidate_count={len(to_send)} min_severity={args.telegram_min_severity}")
        if to_send:
            send_telegram(format_alert_text(to_send))


if __name__ == "__main__":
    main()
