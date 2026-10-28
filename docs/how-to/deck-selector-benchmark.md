# Replay and grade the deck selector

The deck selector (`pipeline/deck_select.py`, `config/decks.yaml`) picks a
recap shortlist from the Jev-judged candidate pool. This runbook replays it
against published recaps, produces label files for owner grading, and scores
both lists once they are graded. Plan:
`docs/exec-plans/active/2026-10-29-deck-candidate-selector.md`.

## 1. Replay

```bash
python3 scripts/deck_replay.py --deck daily --from 2026-10-24 --to 2026-10-27 --packet
python3 scripts/deck_replay.py --deck weekly --week 2026-W44 --packet
```

Each window rebuilds the judged candidates (`pipeline/deck_candidates.py`:
the committed `data/quality/pool/` files plus a backfill from
`data/processed/judgments.json`, run snapshots and `data/raw`), applies the
bundle builder's filters, and runs the selector at the published recap's size.
Judge fields exist from 2026-10-24 onward; earlier windows have no scores to
replay.

The report goes to `data/quality/deck_benchmark/runs/<deck>-<stamp>/`
(`report.md`, `report.json`; gitignored):

- **Funnel**: Jev keeps in the deck's item types -> in any feed edition -> in
  the recap bundle -> in the published recap, and keeps in the shortlist.
- **Published vs selector**: overlap, top sources, and silver must-cover
  recall (multi-source stories and storyline members). Silver favors the
  selector, which scores coverage, and is tiny on single days; it is a smoke
  test, not the benchmark.
- **Labeled metrics** once grades exist.

## 2. Grade

`--packet` writes `data/quality/deck_benchmark/labels/<deck>-<window>.json`
with every story either list picked. For each story:

| field | value |
|---|---|
| `grade` | `2` must-read (the recap is wrong without it), `1` useful, `0` should not be in the recap |
| `same_as` | `story_id` of another story in the file about the same event, else `null` |
| `note` | optional |

`picked_by` says which list chose it. Stories both lists picked are prefilled
with grade `1`; change them only when that is wrong. Disagreements are `null`
and are the ones to grade. Grade the story, not the list: open the URL when
the title is not enough.

Rerunning `--packet` appends new stories and never changes an existing grade.

## 3. Score

Rerun the same replay command. The report adds, for both the published recap
and the selector at the same K:

- **must-cover recall@K**: share of grade-2 stories in the list. This is the
  recall guard; the selector must not lose to the published recap here.
- **alpha-nDCG@K** (alpha 0.5): graded relevance with a discount for repeat
  cards about one event (`same_as`). This is the quality metric.
- **grade sum** and **drops** (grade-0 cards in the list).

Ship gate for turning the selector on for a deck: must-cover recall@K no worse
than the published recap and alpha-nDCG@K better, over the graded windows.

## 4. Tune

Change `config/decks.yaml` (weights, `min_utility`, `max_per_source`, role
and category caps), rerun step 1, and compare. The bench in each selection
names the constraint that kept a story out (`source_cap:<source>`,
`role_cap:<role>`, `category_cap:<category>`, `budget`, `below_min_utility`),
so a binding cap is visible without reading the solver.

## Bundle flag

`build_daily_input.py --selector` and `build_weekly_input.py --selector` add a
`selection` object (shortlist, bench, diagnostics) to the bundle. `articles`
and every other field are unchanged, and the recap skills do not read
`selection` yet.
