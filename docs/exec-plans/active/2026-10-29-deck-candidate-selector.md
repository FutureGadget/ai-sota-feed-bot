# Deck candidate selector: Jev-scored, budgeted selection for the editor decks

## Status

- Phase 1 (judged-pool persistence): implemented 2026-10-29.
- Phases 2-4 (funnel/replay, story-level utility, min-cost-flow selection):
  implemented 2026-10-29 behind `--selector`; recaps unchanged.
- Labels: the first four daily windows (2026-10-24 to 10-27) are waiting for
  owner grades in `data/quality/deck_benchmark/labels/`.
- Phase 5 (agent contract): not started; gated on the labeled benchmark.

Runbook: `docs/how-to/deck-selector-benchmark.md`.

## Problem

The five editor decks (daily recap, weekly recap, Playbook, wiki,
Foundations) are written by agents, and an agent can only write about what its
input bundle contains. Today the daily and weekly bundles are built by
`collect_day_articles` / `collect_week_articles`, which walk
`data/processed/runs/` - the ranked 24-item feed editions - and keep the union.
`pipeline/deck_quality.py` then attaches the Jev verdict and removes known
drops. Three consequences:

1. **Recall is capped by feed layout, not quality.** An item reaches a recap
   only if it won a slot in some two-hour edition. Slot caps, time decay and
   the 24-item merge are presentation limits for the live feed; they are the
   wrong filter for a day-level or week-level summary.
2. **Jev filters but never selects.** The judge score is attached, but the
   bundle is sorted newest-first. The agent picks about half of a daily
   bundle and about a sixth of a weekly bundle with no ordering signal.
3. **Selection is unmeasured.** The Jev gate has a benchmark
   (`pipeline/quality_benchmark.py`); the deck selection step does not.

Measured on the committed artifacts (2026-10-24 to 2026-10-27, release items
excluded, a Jev `keep` counted on its published day):

| day | Jev keeps | in any edition | in daily bundle | in published recap |
|---|---:|---:|---:|---:|
| 2026-10-24 (Sat) | 28 | 17 | 7 | 7 |
| 2026-10-25 (Sun) | 38 | 21 | 16 | 12 |
| 2026-10-26 | 112 | 68 | 19 | 13 |
| 2026-10-27 | 134 | 79 | 37 | 20 |

Most of the gap between "keep" and "daily bundle" is research, which the daily
recap excludes by design (`--types news`). The rest is layout loss: on
2026-10-24, nine Hacker News items the judge kept never reached an edition
because the `community_signal` lane holds four items, so no recap could have
picked them. The weekly bundle (244 items for W43, 42 published) loses about
half of the research keeps the same way.

## Outcome

- The decks read from the **judged candidate pool**, not from the ranked
  editions.
- A deterministic selector produces a **ranked shortlist plus a bench** for
  each deck, under explicit budget, category and source constraints.
- The agent writes from the shortlist and may swap items with a logged reason.
  Swaps become labels.
- Selection quality and recall are measured offline before any prompt change
  ships, and tracked after.

## Design

### Phase 1 - Persist the judged pool (implemented)

`run_ranking` exposes the post-Jev Stage A pool through an optional
`pool_sink`. `pipeline/judged_pool.py` merges each run's pool into
`data/quality/pool/<run-date>.json`: one row per item (URL key), latest judge
fields, a 400-character excerpt, the edition slot, `runs_seen`,
`edition_runs` (how many editions included it) and `best_edition_rank`.
The pool includes unjudged items, so fail-open behavior carries through.
Retention is 14 days (`prune_runtime_data.py --pool-days`). The directory is
under `data/quality/`, which is already excluded from the Vercel deployment.

No ranking, feed or deck behavior changes in this phase. It produces the
dataset every later phase needs and lets the funnel be measured going forward.

### Phase 2 - Funnel report and baseline (implemented)

`pipeline/deck_candidates.py` builds the judged candidates for a published
window from the pool files and, for windows before the pool existed, a
backfill from `judgments.json`, run snapshots and `data/raw`. The backfill
misses unjudged Stage A items that never reached an edition; judge fields
exist from 2026-10-24 (the feed-quality-v2 store reset), so earlier windows
cannot be replayed.

`scripts/deck_replay.py` prints the funnel (keeps -> edition -> bundle ->
recap, and keeps -> shortlist) per window and compares the published recap
with the selector at the same K. Baseline, daily news, 2026-10-24 to 10-27:

| day | Jev keep | in edition | in bundle | in recap | in shortlist (same K) |
|---|---:|---:|---:|---:|---:|
| 10-24 (Sat) | 19 | 10 | 7 | 7 | 6 |
| 10-25 (Sun) | 19 | 16 | 15 | 11 | 5 |
| 10-26 | 22 | 22 | 18 | 12 | 11 |
| 10-27 | 40 | 40 | 38 | 21 | 16 |

Findings:

- For the daily (news only), the pool adds little on weekdays: the bundle
  already holds almost every news keep. The gain is on weekends (10-24: 7 of
  19 keeps reached the bundle) and in composition: published recaps were
  64% Hacker News (36 of 57 cards); the selector caps it at 4 per day, so on
  quiet days it returns 5-8 cards where the recap had 11. Whether those extra
  HN cards are worth reading is the main question the labels answer.
- For the weekly, the pool matters: for 2026-10-24 to 10-28 the judged pool
  holds 300 keeps in the weekly's types against a 228-item edition-based
  bundle.
- Feed position is not a usable must-cover signal: on quiet days the feed's
  top three are Hacker News posts, so "feed lead" measured agreement with the
  feed ranking. Silver must-cover is now multi-source stories and storyline
  members only, and it is a smoke test.

### Phase 3 - Story-level candidates and utility (implemented)

- Collapse the pool to one candidate per story (`story_key`, falling back to
  URL), then join stories whose titles name the same model at the same
  version (`kimi|3.1`). The feed's cluster keys include the headline, so the
  week's largest launch (Kimi K3.1 Pro) was five separate items scoring 0.76
  each, just under the weekly cutoff; merged, it is one seven-member story
  that makes the shortlist. Keep the best-scored member as the card and use
  distinct sources across members as the coverage signal.
- Utility, computed in `pipeline/deck_select.py` with weights in
  `config/decks.yaml`:

  ```text
  u = w_keep * judge_score
    + w_rel  * platform_relevant
    + w_cov  * log1p(source_count - 1)
    + w_tune * source_tune
    + w_ed   * [appeared in an edition]
    - w_mkt  * corporate_marketing
  ```

  Unjudged items get `scale` times the median judged score of their source
  role, never zero, so fail-open survives. Release items are scored by their
  deterministic tier (`release.major/minor`), because the Brief gate answers
  "drop" for release notes by design.

### Phase 4 - Budgeted selection with min-cost max-flow (implemented)

Per deck, solve a min-cost flow on:

```text
S -> role_r          capacity = per-role cap (research, release, community...)
role_r -> source_j   capacity = per-source cap (deck config)
source_j -> item_i   capacity 1, cost = -round(u_i * 1000)
item_i -> category_c capacity 1
category_c -> T      floor edge: capacity = min_c, cost = -BIG
                     rest edge:  capacity = max_c - min_c, cost 0
total flow <= K      (deck budget: daily ~15, weekly ~40)
```

Successive shortest paths stop when the next augmenting path has
non-negative cost, so a quiet day yields a shorter recap instead of filler
(items below `min_utility` get no edge). The network is valid because each
item has exactly one source and one category; story collapse in Phase 3
removes the third partition (one card per story) before the solve. Each
source has one role, so role caps nest the source caps and the network stays
exact. Role caps were added after the first weekly replay: with category caps
only, 27 of 40 weekly picks were arXiv papers. `pipeline/mincostflow.py` is a
dependency-free successive-shortest-path solver (Dijkstra with potentials);
it matches a brute-force oracle on 80 random instances, and a weekly solve
over about 400 stories takes well under a second. If later constraints stop nesting (for example a cap per
company across sources), switch the solver to an ILP; the utility and
config stay.

Output: `shortlist` (the flow solution, ordered by utility) and `bench` (the
next N by utility that the solution excluded, with the binding constraint
named). The bundle builders' `--selector` flag (off by default) adds both as
`selection`; `articles` is unchanged until Phase 5.

### Phase 5 - Agent contract and rollout

The deck skills change to: write from `shortlist`; swap in a `bench` item
only with a one-line `swap_reason` in the recap JSON. Swaps and
shortlist-items-not-used are logged to `data/quality/deck_feedback.jsonl`
and feed the label set.

## Evaluation

F1 measures the Jev keep/drop gate well and stays the gate metric. A deck is
a fixed-budget selection, where precision and recall move together and F1
hides the trade-off, so the selector is measured with:

| metric | measures | role |
|---|---|---|
| Must-cover recall@K | share of must-include stories in the shortlist | recall guard (ship blocker) |
| alpha-nDCG@K (alpha = 0.5) | graded relevance with a penalty for repeating a story/subtopic | primary quality metric |
| Utility ratio | selected utility / oracle utility under the same constraints, using labeled grades | checks the solver, not the scores |
| Stage recall | keep -> pool -> shortlist -> published | locates loss |
| Swap rate | share of shortlist items the agent replaces | online drift signal |

Labels:

- Grades 0 (drop) / 1 (useful) / 2 (must-read) per story, owner-adjudicated,
  in `data/quality/deck_benchmark/labels/<deck>-<window>.json`.
- Must-cover set: grade 2. Silver (multi-source, storyline member) is a
  smoke test only.
- Disagreement labeling: replay the selector on the last four weeks of
  bundles and label only stories where the selector and the published recap
  disagree. Agreements carry little information.
- Extend the frozen Jev benchmark with a fresh holdout week first. The current
  50-item sample scores F1 1.0, which bounds recall only above roughly 0.84 at
  95% confidence and was partly used to tune the rubric.

Ship gate for each deck: must-cover recall@K no worse than baseline, and
alpha-nDCG@K better, on the replayed weeks.

## Rollout order

1. Phase 1 lands; pool accumulates for 14 days. (done, pending merge)
2. Phases 2-4 behind `--selector`. (done)
3. Owner grades the four daily windows; replay the first full weekly
   (2026-W44) after its recap publishes and grade it.
4. Tune `config/decks.yaml` against the grades, chiefly the per-source cap
   for Hacker News and `min_utility`.
5. Phase 5 for weekly first (largest bundle, largest expected gain), then
   daily, then Playbook/wiki/Foundations.

## Rollback

Phase 1: remove the `pool_sink` argument in `pipeline/build_digest.py`; the
pool stops growing and prunes out in 14 days. Phases 2-4 change no production
path: the selector runs only under `--selector` or `scripts/deck_replay.py`.
