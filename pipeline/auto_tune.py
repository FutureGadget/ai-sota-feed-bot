#!/usr/bin/env python3
"""Auto-tune source weights from reader feedback + click-through signal (v1.3).

Blends two signals per source over a rolling window:
  - explicit: net reader feedback (useful / irrelevant / hype) from
    data/feedback/events.jsonl
  - implicit: click-through rate — per-source clicks pulled from PostHog
    (`sync-ctr` writes data/feedback/ctr_clicks.json) divided by rank-weighted
    exposure computed locally from data/processed/runs snapshots (the web
    client only reports batched impression counts, so exposure cannot come
    from PostHog)

The result is an additive per-source adjustment layered on top of the
hand-tuned `source_bias` in config/ranking.yaml. Guardrails: minimum sample
sizes before a source moves, a hard cap on adjustment magnitude, and a
staleness cutoff in the ranking-side loader so an abandoned artifact stops
steering scores. The rolling window is the decay: old events simply age out.

Commands:
  sync-ctr  pull per-source click counts from PostHog -> data/feedback/ctr_clicks.json
            (uses POSTHOG_PERSONAL_API_KEY / POSTHOG_PROJECT_ID; no-op without them)
  report    dry-run: print proposed adjustments and the inputs behind them
  apply     write data/feedback/source_adjustments.json for the ranking pipeline

Knobs live in config/ranking.yaml under `auto_tune:` (see DEFAULTS).
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RANKING_CFG_FILE = ROOT / "config" / "ranking.yaml"
RUNS_DIR = ROOT / "data" / "processed" / "runs"
CTR_CLICKS_PATH = ROOT / "data" / "feedback" / "ctr_clicks.json"
ADJUSTMENTS_PATH = ROOT / "data" / "feedback" / "source_adjustments.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feedback import load_events, net_events, parse_ts, utc_now  # noqa: E402

DEFAULTS = {
    "enabled": False,  # ranking-side gate; tuner itself always runs
    "window_days": 30,
    "max_abs_adjustment": 0.15,
    "explicit_weight": 0.10,  # delta for a source with unanimously useful feedback
    "ctr_weight": 0.08,       # delta per doubling/halving of CTR vs global CTR
    "min_explicit_events": 3,
    "min_exposure": 25.0,
    "ctr_smoothing_exposure": 20.0,  # empirical-Bayes prior mass pulling CTR to global
    "max_age_days": 14,  # ranking ignores an adjustments file older than this
}


def load_tune_cfg() -> dict:
    cfg = dict(DEFAULTS)
    try:
        raw = yaml.safe_load(RANKING_CFG_FILE.read_text(encoding="utf-8")) or {}
        cfg.update(raw.get("auto_tune", {}) or {})
    except FileNotFoundError:
        pass
    return cfg


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def iter_window_runs(window_days: int) -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    cutoff = utc_now() - timedelta(days=window_days)
    runs = []
    for p in RUNS_DIR.rglob("*.json"):
        run = read_json(p, None)
        if not isinstance(run, dict) or not isinstance(run.get("items"), list):
            continue
        run_at = parse_ts(run.get("run_at"))
        if run_at and run_at >= cutoff:
            runs.append(run)
    return runs


def compute_exposure(runs: list[dict]) -> tuple[dict[str, float], dict[str, str]]:
    """Rank-weighted appearance count per source, plus a url -> source map.

    Weight 1/log2(rank+1) (DCG-style) approximates how much of the feed a
    reader actually sees: rank 1 counts ~1.0, rank 15 counts ~0.25.
    """
    exposure: dict[str, float] = {}
    url_to_source: dict[str, str] = {}
    for run in runs:
        for rank, it in enumerate(run.get("items") or [], start=1):
            src = str(it.get("source") or "").strip()
            if not src:
                continue
            exposure[src] = exposure.get(src, 0.0) + 1.0 / math.log2(rank + 1)
            url = str(it.get("url") or "").strip()
            if url:
                url_to_source.setdefault(url, src)
    return exposure, url_to_source


def explicit_counts(window_days: int, url_to_source: dict[str, str]) -> dict[str, dict[str, int]]:
    cutoff = utc_now() - timedelta(days=window_days)
    recent = [
        e for e in load_events()
        if (parse_ts(e.get("ts")) or utc_now()) >= cutoff
    ]
    counts: dict[str, dict[str, int]] = {}
    for ev in net_events(recent):
        src = str(ev.get("item_source") or "").strip() or url_to_source.get(str(ev.get("url") or "").strip(), "")
        signal = str(ev.get("signal") or "")
        if not src or signal not in ("useful", "irrelevant", "hype"):
            continue
        per = counts.setdefault(src, {"useful": 0, "irrelevant": 0, "hype": 0})
        per[signal] += 1
    return counts


def load_clicks(cfg: dict) -> dict[str, float]:
    data = read_json(CTR_CLICKS_PATH, None)
    if not isinstance(data, dict):
        return {}
    generated = parse_ts(data.get("generated_at"))
    if not generated or (utc_now() - generated).days > int(cfg["max_age_days"]):
        return {}
    clicks = data.get("clicks") or {}
    return {str(k): float(v) for k, v in clicks.items() if float(v) > 0}


def compute_adjustments(cfg: dict) -> dict:
    window_days = int(cfg["window_days"])
    runs = iter_window_runs(window_days)
    exposure, url_to_source = compute_exposure(runs)
    feedback = explicit_counts(window_days, url_to_source)
    clicks = load_clicks(cfg)

    total_exposure = sum(exposure.values())
    total_clicks = sum(clicks.get(s, 0.0) for s in exposure)
    global_ctr = (total_clicks / total_exposure) if total_exposure > 0 else 0.0

    cap = float(cfg["max_abs_adjustment"])
    k = float(cfg["ctr_smoothing_exposure"])
    details: dict[str, dict] = {}
    adjustments: dict[str, float] = {}

    for src in sorted(set(exposure) | set(feedback)):
        fb = feedback.get(src, {})
        n_fb = sum(fb.values())
        delta_explicit = 0.0
        if n_fb >= int(cfg["min_explicit_events"]):
            score = (fb.get("useful", 0) - fb.get("irrelevant", 0) - fb.get("hype", 0)) / n_fb
            delta_explicit = float(cfg["explicit_weight"]) * score

        exp_s = exposure.get(src, 0.0)
        delta_ctr = 0.0
        ctr_ratio = None
        if global_ctr > 0 and exp_s >= float(cfg["min_exposure"]):
            smoothed_ctr = (clicks.get(src, 0.0) + k * global_ctr) / (exp_s + k)
            ctr_ratio = smoothed_ctr / global_ctr
            # log2: +ctr_weight per doubling of CTR vs global; clamp ratio
            # influence to two doublings so outliers can't dominate.
            delta_ctr = float(cfg["ctr_weight"]) * max(-2.0, min(2.0, math.log2(ctr_ratio)))

        total = max(-cap, min(cap, delta_explicit + delta_ctr))
        details[src] = {
            "exposure": round(exp_s, 1),
            "clicks": clicks.get(src, 0.0),
            "ctr_ratio": round(ctr_ratio, 3) if ctr_ratio is not None else None,
            "feedback": fb or None,
            "delta_explicit": round(delta_explicit, 4),
            "delta_ctr": round(delta_ctr, 4),
            "delta_total": round(total, 4),
        }
        if abs(total) >= 0.005:
            adjustments[src] = round(total, 3)

    return {
        "generated_at": utc_now().isoformat(),
        "window_days": window_days,
        "runs_in_window": len(runs),
        "global_ctr": round(global_ctr, 5),
        "config": {key: cfg[key] for key in DEFAULTS if key != "enabled"},
        "adjustments": adjustments,
        "details": details,
    }


def print_report(result: dict) -> None:
    print(
        f"auto_tune window={result['window_days']}d runs={result['runs_in_window']} "
        f"global_ctr={result['global_ctr']} adjusted_sources={len(result['adjustments'])}"
    )
    rows = sorted(result["details"].items(), key=lambda kv: -abs(kv[1]["delta_total"]))
    header = f"{'source':<32} {'exposure':>9} {'clicks':>7} {'ctr_x':>6} {'fb(u/i/h)':>10} {'d_exp':>7} {'d_ctr':>7} {'total':>7}"
    print(header)
    for src, d in rows:
        fb = d["feedback"] or {}
        fb_s = f"{fb.get('useful', 0)}/{fb.get('irrelevant', 0)}/{fb.get('hype', 0)}" if fb else "-"
        ctr_s = f"{d['ctr_ratio']:.2f}" if d["ctr_ratio"] is not None else "-"
        print(
            f"{src:<32} {d['exposure']:>9} {d['clicks']:>7} {ctr_s:>6} {fb_s:>10} "
            f"{d['delta_explicit']:>7} {d['delta_ctr']:>7} {d['delta_total']:>7}"
        )


def cmd_report(args: argparse.Namespace) -> int:
    print_report(compute_adjustments(load_tune_cfg()))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    cfg = load_tune_cfg()
    result = compute_adjustments(cfg)
    print_report(result)

    # Skip the write when nothing changed and the artifact is still fresh,
    # so daily runs don't churn commits; rewrite before it goes stale so the
    # ranking-side max_age guard keeps trusting confirmed values.
    existing = read_json(ADJUSTMENTS_PATH, None)
    if isinstance(existing, dict) and existing.get("adjustments") == result["adjustments"]:
        generated = parse_ts(existing.get("generated_at"))
        if generated and (utc_now() - generated).days < int(cfg["max_age_days"]) / 2:
            print("auto_tune_apply skipped=unchanged")
            return 0

    ADJUSTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADJUSTMENTS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"auto_tune_apply wrote={os.path.relpath(ADJUSTMENTS_PATH, ROOT)} adjustments={len(result['adjustments'])}")
    return 0


def cmd_sync_ctr(args: argparse.Namespace) -> int:
    api_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.environ.get("POSTHOG_PROJECT_ID", "").strip()
    host = (os.environ.get("POSTHOG_API_HOST", "").strip() or "https://us.posthog.com").rstrip("/")
    if not api_key or not project_id:
        print("ctr_sync_skipped reason=missing_credentials")
        return 0

    import requests

    window_days = int(load_tune_cfg()["window_days"])
    since = utc_now() - timedelta(days=window_days)
    hogql = (
        "SELECT properties.source, count() FROM events "
        "WHERE event = 'click' AND notEmpty(toString(properties.source)) "
        f"AND timestamp >= toDateTime('{since.strftime('%Y-%m-%d %H:%M:%S')}') "
        "GROUP BY properties.source ORDER BY count() DESC LIMIT 500"
    )
    resp = requests.post(
        f"{host}/api/projects/{project_id}/query",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": {"kind": "HogQLQuery", "query": hogql}},
        timeout=60,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []

    clicks = {str(src): int(n) for src, n in results if src and int(n) > 0}
    CTR_CLICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CTR_CLICKS_PATH.write_text(
        json.dumps(
            {"generated_at": utc_now().isoformat(), "window_days": window_days, "clicks": clicks},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"ctr_sync_done sources={len(clicks)} total_clicks={sum(clicks.values())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="dry-run: print proposed adjustments").set_defaults(func=cmd_report)
    sub.add_parser("apply", help="write data/feedback/source_adjustments.json").set_defaults(func=cmd_apply)
    sub.add_parser("sync-ctr", help="pull per-source click counts from PostHog").set_defaults(func=cmd_sync_ctr)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
