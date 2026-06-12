#!/usr/bin/env python3
"""One-time enrichment backfill for the story store via the Message Batches API.

Story permalink pages (/story/<sid>) render whatever data/stories/<month>.json
holds. Stories captured while LLM labeling was disabled carry keyword-echo
why_it_matters ("Matches feed focus: ...") or no why at all. This script
labels them with the same prompt/schema the live pipeline uses, at 50% batch
pricing, and writes the results back into the store.

Usage:
  python scripts/backfill_story_labels.py plan              # candidates + cost estimate
  python scripts/backfill_story_labels.py submit            # create the batch
  python scripts/backfill_story_labels.py status            # poll processing status
  python scripts/backfill_story_labels.py apply             # write results into data/stories/

After apply: python pipeline/render_static_pages.py && commit data/stories/ web/
Requires ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import llm_label  # noqa: E402
import story_store  # noqa: E402

STATE_FILE = ROOT / "data" / "llm" / "backfill_batch.json"
GENERIC_WHY_PREFIX = "Matches feed focus"
MAX_OUTPUT_TOKENS = 512


def needs_enrichment(rec: dict) -> bool:
    why = str(rec.get("why_it_matters") or "").strip()
    summary = str(rec.get("summary") or "")
    return (
        not why
        or why.startswith(GENERIC_WHY_PREFIX)
        or "Article URL:" in summary
        or not str(rec.get("summary_1line") or "").strip()
    )


def candidates() -> dict[str, dict]:
    stories = story_store.load_store()
    return {sid: rec for sid, rec in stories.items() if needs_enrichment(rec)}


def batch_request(sid: str, rec: dict, cfg: dict, prefs: dict, prompt_text: str) -> dict:
    item = {
        "title": rec.get("title", ""),
        "summary": rec.get("summary", "") or rec.get("summary_1line", ""),
        "source": rec.get("source", ""),
        "url": rec.get("url", ""),
        "type": rec.get("type", ""),
    }
    return {
        "custom_id": sid,
        "params": {
            "model": cfg.get("model", "claude-haiku-4-5"),
            "max_tokens": MAX_OUTPUT_TOKENS,
            "system": prompt_text,
            "messages": [{"role": "user", "content": llm_label.label_user_payload(item, prefs)}],
            "output_config": {"format": {"type": "json_schema", "schema": llm_label.LABEL_SCHEMA}},
        },
    }


def cmd_plan() -> None:
    cand = candidates()
    cfg = llm_label.load_cfg()
    prefs = llm_label.load_preferences()
    prompt_text = llm_label.load_prompt_text()
    in_chars = sum(
        len(prompt_text) + len(llm_label.label_user_payload(rec, prefs)) for rec in cand.values()
    )
    in_mtok = in_chars / 4 / 1e6  # rough chars->tokens
    out_mtok = len(cand) * 250 / 1e6
    # Haiku 4.5 batch pricing: $0.50 in / $2.50 out per MTok
    est = in_mtok * 0.50 + out_mtok * 2.50
    print(f"stories needing enrichment: {len(cand)}")
    print(f"estimated tokens: ~{in_mtok:.2f}M in / ~{out_mtok:.2f}M out")
    print(f"estimated batch cost (claude-haiku-4-5, 50% off): ~${est:.2f}")


def cmd_submit() -> None:
    import anthropic

    cand = candidates()
    if not cand:
        print("nothing to backfill")
        return
    cfg = llm_label.load_cfg()
    prefs = llm_label.load_preferences()
    prompt_text = llm_label.load_prompt_text()
    requests = [batch_request(sid, rec, cfg, prefs, prompt_text) for sid, rec in cand.items()]

    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"batch_id": batch.id, "submitted": len(requests)}, indent=2), encoding="utf-8"
    )
    print(f"submitted batch {batch.id} with {len(requests)} requests")
    print("poll with: python scripts/backfill_story_labels.py status")


def _load_state() -> dict:
    if not STATE_FILE.exists():
        sys.exit("no batch state — run `submit` first")
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def cmd_status() -> None:
    import anthropic

    state = _load_state()
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"batch {batch.id}: {batch.processing_status}")
    print(
        f"processing={batch.request_counts.processing} "
        f"succeeded={batch.request_counts.succeeded} "
        f"errored={batch.request_counts.errored} "
        f"expired={batch.request_counts.expired}"
    )


def cmd_apply() -> None:
    import anthropic

    state = _load_state()
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        sys.exit(f"batch not finished yet: {batch.processing_status}")

    stories = story_store.load_store()
    applied = errored = skipped = 0
    for result in client.messages.batches.results(state["batch_id"]):
        if result.result.type != "succeeded":
            errored += 1
            continue
        rec = stories.get(result.custom_id)
        if rec is None:
            skipped += 1
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            label = json.loads(text)
        except json.JSONDecodeError:
            errored += 1
            continue
        why = str(label.get("why_1line") or "").strip()
        summary_1line = str(label.get("summary_1line") or "").strip()
        if why:
            rec["why_it_matters"] = why
        if summary_1line:
            rec["summary_1line"] = summary_1line
        applied += 1

    story_store.write_store(stories)
    print(f"applied={applied} errored={errored} skipped={skipped}")
    print("next: python pipeline/render_static_pages.py, then commit data/stories/ + web/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "submit", "status", "apply"])
    args = parser.parse_args()
    {"plan": cmd_plan, "submit": cmd_submit, "status": cmd_status, "apply": cmd_apply}[args.command]()


if __name__ == "__main__":
    main()
