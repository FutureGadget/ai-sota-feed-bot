# Jev recalibration, 2026-10-26

Follow-up to `jev-quality-benchmark-2026-10-24.md`. That run found three concrete
misses (the Bashkir paper, the DeepSeek search scoop, and OpenAI models on
Google Cloud) and suggested hard-positive examples. The 2026-10-25 daily recap
made the failure visible: 10 of 11 cards came from Hacker News because the
search lane scored every item below the headroom floor.

## Diagnosis

The judge was not miscalibrated so much as under-informed. The same item, same
model, same rubric scored:

| item | excerpt | score |
|---|---|---:|
| `bench-004` SLM vocabulary, 77% inference cost cut | 2,500 chars | 0.70 |
| `bench-004` same item | empty | **0.04** |
| `bench-049` Beam 501B open model | 2,500 chars | 0.85 |
| `bench-049` same item | empty | **0.03** |
| `bench-013` OpenAI models on Google Cloud | 1,864 chars | 0.13 |
| `bench-013` same item | 142 chars | 0.06 |

Three structural causes in the pipeline:

1. `content_fetch._should_fetch_paragraph` skips `search_*` and
   `news.google.com`, so search items are judged from a ~76-character Google
   News snippet. The rubric says a teaser is not evidence, so the model
   correctly answered low every time.
2. `judgment_key` did not include the excerpt, so a snippet-only judgment was
   reused for 14 days even after the article body was available.
3. The rubric treated model availability, pricing, and API changes as
   corporate news. `bench-013` (OpenAI models on Google Cloud) and `bench-018`
   (Data Agent Kit GA) were the labeled hard positives it missed.

## What changed

- **Evidence floor.** `content_fetch.min_evidence_chars: 300`. Below that
  (releases exempt), `apply_judge` returns `judge_verdict: unjudged` with
  `judge_error: insufficient_evidence` and no score. Unjudged items pass the
  headroom floor, so the deterministic policy decides instead of a
  snippet-driven 0.04.
- **Evidence-aware store key.** `judgment_key` now includes an evidence bucket,
  and store entries persist `judge_evidence_chars`. A thin-evidence judgment
  is refreshed after enrichment instead of being reused.
- **Rubric v2 (`feed-quality-v2`).** Added keep rules for model availability,
  price/quota, API surface, and Day-0 serving changes; added a drop rule for
  domain-specific adaptation papers; clarified that a concrete change in the
  title is evidence even when the excerpt is short; clarified the
  `corporate_marketing` question to exclude those changes.
- **Operating point.** `judge.keep_at: 0.35` and
  `ranking.judge_ranking.headroom_min_score: 0.35`, matching the recalibrated
  score distribution (see `docs/QUALITY_SCORE.md`).

## Benchmark after recalibration

Same 50 frozen items, same 21 keep / 29 drop labels, same 2,500-character
excerpts (bench-026 is the one title-only item).

| metric | v1 (2026-10-24) | v2 (2026-10-26) |
|---|---:|---:|
| AUC | 0.969 | **1.000** |
| F1 at tuned threshold | 0.927 (0.25) | **1.000** (0.35) |
| precision | 0.950 | **1.000** |
| recall | 0.905 | **1.000** |
| Brier | 0.095 | **0.024** |
| ECE(10) | 0.114 | 0.112 |
| false positives | 1 | **0** |
| false negatives | 2 | **0** |

Previously failing items after v2:

- `bench-013` OpenAI models on Google Cloud: 0.13 to **0.90**
- `bench-018` Data Agent Kit GA: 0.20 to **0.47**
- `bench-026` DeepSeek search scoop: 0.04 to **0.71** (from the title alone).
  In production its 76-character Google News snippet is below the 300-character
  evidence floor, so it stays `unjudged` and passes through headroom instead.
- `bench-032` DeepSeek web-search pricing: 0.35 to **0.87**
- `bench-044` Bashkir adaptation paper: 0.53 to **0.14**
- `bench-004` SLM vocabulary: 0.04 (thin) to **0.65**
- `bench-049` Beam 501B: 0.03 (thin) to **0.97**

The gap between the highest drop that reaches the ranking (0.14) and the
lowest keep (0.47) makes 0.35 a safe operating point.

## Replay on the incident day

Replaying the 2026-10-25 15:04 candidate pool through `apply_pre_ranking ->
apply_judge -> run_ranking` with the new policy:

- v1: 0 search cards, 3 Hacker News cards, search judged 0.01-0.07.
- v2 + evidence floor: **1 search card, 3 Hacker News cards**, 24-item edition,
  search item unjudged (thin evidence) and admitted through headroom.

The mix is stable for `headroom_min_score` 0.2-0.45 and `judge_ranking.weight`
0.6-1.2 on that day; the floor is not the thing holding the lane open.

## Caveat

The rubric examples were adjusted on this benchmark, so a perfect score is
partly in-sample. The benchmark is 50 assistant-labeled items, not a gold set.
Before treating AUC 1.0 as general, relabel a fresh sample from a later week and
rerun `python3 pipeline/quality_benchmark.py run --provider openrouter`.

Cost was unchanged: 50 hybrid requests, ~$0.003.
