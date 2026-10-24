# Jev quality benchmark

A small, frozen sample of the feed's candidate pool for testing whether a
decision model (Jev) is a useful quality gate. It is not a production data
set and it is not a substitute for the owner's judgment.

## Files

- `items.json` - 50 benchmark items with title, source, published date, a
  body excerpt, the expected binary label (`keep`/`drop`), a fine label
  (`must_read`/`useful`/`filler`/`junk`), and a short rationale.
- `labels.md` - the same labels in a review table. Edit `items.json` after
  correcting a row, then regenerate the table with
  `python3 scripts/build_quality_benchmark.py`.
- `content_cache.json` - fetched article text used to build the excerpts.
  This keeps the benchmark reproducible offline and out of the article
  network at run time.
- `fixture_scores.json` - synthetic scores for validating the harness and
  the review packet. **Not Jev output.** Every report built from it says so.
- `runs/` - generated benchmark runs (`report.md`, `report.json`,
  `predictions.json`, `review.md`). Not committed.

## Slices

The sample is stratified so a single easy slice cannot make a judge look good:

| slice | what it tests |
|---|---|
| `first_party_engineering` | substantive first-party engineering should survive |
| `first_party_marketing` | ads, customer stories, offices, partnerships, funding |
| `practitioner_analysis` | practitioner deep dives vs off-topic link-blog posts |
| `search_seo` | comparison listicles and explainers vs a genuine search scoop |
| `search_business_gossip` | funding, IPO, executive, outage, and consumer-hardware noise |
| `off_topic_domain` | clinical, biology, forestry, protein, and math posts |
| `research` | agent/inference/eval papers vs niche domain adaptation |
| `releases` | routine version bumps vs substantive release engineering |

There are deliberate hard positives (a relevant corporate announcement, a
genuine search scoop, a substantive Day-0 serving post) and hard negatives
(a corporate post that sounds technical, an off-topic post that mentions
agents).

## Label policy

- `must_read`: a platform/agent engineer should read it this week.
- `useful`: worth keeping in the brief; concrete and relevant, not
  necessarily essential.
- `filler`: on-topic-ish but low value; should not take a story slot.
- `junk`: marketing, SEO, gossip, off-mission, or routine release noise.

Binary `keep` = `must_read` + `useful`; `drop` = `filler` + `junk`.

The labels are **assistant-authored and provisional**. The benchmark exists
to surface disagreements for the owner to adjudicate, not to declare a
ground truth. A judge that agrees with the labels is not automatically good;
it may simply share the label author's biases.

## Run

```bash
# Validate the harness with synthetic scores
python3 pipeline/quality_benchmark.py run \
  --provider fixture \
  --scores data/quality/benchmark/fixture_scores.json

# Deterministic baseline (not a judge)
python3 pipeline/quality_benchmark.py run --provider heuristic

# Real Jev run (requires config/judge.yaml endpoint + JEV_API_KEY)
python3 pipeline/quality_benchmark.py run --provider jev
```

Read `runs/<provider>-<timestamp>/report.md` first, then `review.md` for the
false positives, false negatives, and ambiguous scores.

## What "good" looks like

- Beat the heuristic baseline on the same labels, not just on accuracy.
- Clear both precision and recall floors at a threshold that is useful for
  the feed (precision matters more: a junk card costs a story slot).
- Report Brier and ECE; a high AUC with bad calibration is not enough.
- Win on the hard slices (`first_party_marketing`, `search_seo`,
  `off_topic_domain`) rather than only on the easy first-party engineering
  items.
- Produce a review packet with disagreements that are genuinely worth
  discussing, not obvious label errors.
