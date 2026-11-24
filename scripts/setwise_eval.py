"""Does setwise comparison rank recap stories better than Jev's score?

Reads the owner grades in ``data/quality/deck_benchmark/labels/<deck>-<day>.json``,
asks Claude to rank small groups of each day's graded stories against each
other (``pipeline/setwise.py``), fits Bradley-Terry scores per day, and reports
how well each signal separates stories graded useful (1-2) from stories graded
"should not be in the recap" (0): AUC within each day, pooled over days, next to
Jev's ``judge_score`` on the same stories. Offline only; nothing reads the
result.

    python scripts/setwise_eval.py                       # Sonnet, 8 per group, 4 rounds
    python scripts/setwise_eval.py --model claude-haiku-5-5 --rounds 6

Needs Anthropic credentials (the same as the translator); spend goes to the
shared ledger and stops at its monthly cap. Writes
``data/quality/deck_benchmark/runs/setwise-<stamp>/report.json`` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import string
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import setwise  # noqa: E402
import translator  # noqa: E402

LABELS_DIR = ROOT / "data" / "quality" / "deck_benchmark" / "labels"
RUNS_DIR = ROOT / "data" / "quality" / "deck_benchmark" / "runs"

SYSTEM = """You are the editor of a daily AI news recap for engineers who build and operate AI systems: AI platform engineers and agent builders. They read it to catch up in ten minutes.

Rank the stories you are given from most to least worth a place in today's recap for that reader. Favour stories that change what such an engineer builds, runs, evaluates or pays for: agent runtimes, tool use, evals, reliability, inference and serving, cost, security that changes engineering practice, and significant model releases. Rank down generic AI news, opinion without new facts, marketing, prompt tips, and stories only loosely about AI.

Reply with a JSON object with one key, "ranking": the story letters in order, best first, separated by commas, using every letter exactly once."""


def load_days(deck: str) -> list[tuple[str, list[dict]]]:
    days = []
    for path in sorted(LABELS_DIR.glob(f"{deck}-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        stories = [
            {"id": sid, **row}
            for sid, row in (data.get("stories") or {}).items()
            if isinstance(row, dict) and row.get("grade") in (0, 1, 2)
        ]
        if stories:
            days.append((str(data.get("window") or path.stem), stories))
    return days


def group_prompt(stories: list[dict]) -> tuple[str, dict[str, str]]:
    letters = {}
    lines = []
    for letter, story in zip(string.ascii_uppercase, stories):
        letters[letter] = story["id"]
        summary = " ".join(str(story.get("summary") or "").split())[:400]
        lines.append(f"{letter}. {story.get('title', '')}\n   source: {story.get('source', '')}\n   {summary}")
    return "Stories:\n\n" + "\n\n".join(lines), letters


def parse_ranking(text: str, letters: dict[str, str]) -> list[str] | None:
    order = [part.strip().upper() for part in str(text).split(",") if part.strip()]
    if sorted(order) != sorted(letters):
        return None
    return [letters[letter] for letter in order]


def evaluate(days, rank_group, size: int, rounds: int) -> dict:
    report = {"days": [], "pooled": {}}
    pooled_setwise, pooled_jev = [], []
    for day, stories in days:
        by_id = {s["id"]: s for s in stories}
        pairs, invalid = [], 0
        for index, group in enumerate(setwise.make_groups(list(by_id), size=size, rounds=rounds, seed=zlib.crc32(day.encode()))):
            ranking = rank_group([by_id[i] for i in group], f"{day}:{index}")
            if ranking is None:
                invalid += 1
                continue
            pairs.extend(setwise.pairs_from_ranking(ranking))
        scores = setwise.bradley_terry(by_id, pairs)
        positive = {i for i, s in by_id.items() if s["grade"] >= 1}
        negative = {i for i, s in by_id.items() if s["grade"] == 0}
        jev = {i: float(s["judge_score"]) for i, s in by_id.items() if s.get("judge_score") is not None}
        row = {
            "day": day,
            "stories": len(by_id),
            "useful": len(positive),
            "not_recap": len(negative),
            "comparisons": len(pairs),
            "invalid_groups": invalid,
            "auc_setwise": setwise.auc(scores, positive, negative),
            "auc_jev": setwise.auc(jev, positive, negative),
            "scores": {i: round(v, 3) for i, v in sorted(scores.items(), key=lambda kv: -kv[1])},
        }
        report["days"].append(row)
        # Pool by within-day rank position so days with different scales mix.
        for signal, sink in ((scores, pooled_setwise), (jev, pooled_jev)):
            ranked = sorted((i for i in signal), key=lambda i: signal[i])
            n = max(len(ranked) - 1, 1)
            sink.extend((f"{day}|{i}", pos / n, by_id[i]["grade"]) for pos, i in enumerate(ranked))
    for name, rows in (("auc_setwise", pooled_setwise), ("auc_jev", pooled_jev)):
        scores = {key: value for key, value, _ in rows}
        report["pooled"][name] = setwise.auc(
            scores, {k for k, _, g in rows if g >= 1}, {k for k, _, g in rows if g == 0}
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deck", default="daily")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--size", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=4)
    args = parser.parse_args()

    days = load_days(args.deck)
    if not days:
        sys.exit(f"no graded stories under {LABELS_DIR}")
    if not translator.is_configured():
        sys.exit("setwise_eval needs Anthropic credentials (see docs/how-to/translation-budget-and-quota.md)")
    client = translator.make_client()
    ledger = translator.Ledger(translator.DEFAULT_LEDGER_PATH)
    spent = {"usd": 0.0, "calls": 0}

    def rank_group(stories: list[dict], key: str) -> list[str] | None:
        user, letters = group_prompt(stories)
        try:
            fields, cost = translator.request_json(
                model=args.model, system_text=SYSTEM, user=user, keys={"ranking"},
                field_chars=80, key=f"setwise:{key}", surface="setwise_eval",
                client=client, ledger=ledger,
            )
        except translator.TranslationError:
            return None
        spent["usd"] += cost
        spent["calls"] += 1
        return parse_ranking(fields["ranking"], letters)

    report = evaluate(days, rank_group, args.size, args.rounds)
    report.update({"model": args.model, "size": args.size, "rounds": args.rounds, **spent})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RUNS_DIR / f"setwise-{stamp}" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in report["days"]:
        print(f"setwise_day day={row['day']} stories={row['stories']} auc_setwise={row['auc_setwise']} auc_jev={row['auc_jev']} invalid_groups={row['invalid_groups']}")
    pooled = report["pooled"]
    print(f"setwise_eval model={args.model} calls={spent['calls']} usd={spent['usd']:.4f} "
          f"auc_setwise={pooled['auc_setwise']} auc_jev={pooled['auc_jev']} report={out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
