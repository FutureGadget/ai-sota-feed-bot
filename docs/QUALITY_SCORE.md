# QUALITY_SCORE.md

## Candidate quality dimensions
- Relevance precision
- Freshness
- Diversity (papers/news/releases)
- Actionability of summary
- Low duplication

Track these over time as v1.2+ lands.

## Editorial guardrails (2026-10-24)

The deterministic editorial policy in `pipeline/editorial.py` makes these
measurable on every build:

- **Same-story duplicates:** zero cards sharing one `story_key` in a served
  feed; cross-source echoes go to `also_covered`.
- **Repeat rate:** share of cards seen in the previous edition. The
  seen-memory should keep this low without emptying a quiet day.
- **Search share:** at most one search-result card in the final feed
  (`editorial_caps.max_search_items`) and one per query in the API pool.
- **First-party coverage:** fresh Anthropic/OpenAI/DeepMind/Claude engineering
  posts included within their freshness window. Corporate newsroom posts are
  reported separately and cannot satisfy the engineering seat.
- **Release coverage:** share of tracked model releases with a first-party or
  high-quality card within 24h.
- **Precision@10:** on a small human-labeled sample, the share of cards a staff
  platform engineer would call useful or must-read.

Reader CTR is a guardrail, not the objective. A clickbait card can win CTR
while losing the finishable, anti-hype product promise.

The offline Jev/decision-model benchmark and review workflow live in
`docs/how-to/jev-quality-benchmark.md`.

## Jev semantic gate (2026-10-24)

The edition builder runs Jev 1.14 as a semantic layer after the Stage A
candidate pool:

- four `noul` questions: `keep`, `platform_relevant`, `release_lane`,
  `corporate_marketing`
- one `choice` question for the primary category
- `keep` is the primary score; release/marketing highs and low platform
  relevance clamp it
- the score is a continuous Stage C weight plus a headroom floor, not a global
  binary gate
- release-role items are exempt from the headroom floor so the Releases tab
  and model radar keep their data
- paragraph excerpts are fetched for candidates whose feed teaser is too short
- prior judgments are reused from `data/processed/judgments.json`; only new or
  changed candidates call Jev

Offline benchmark: AUC 0.969, F1 0.927 at threshold 0.25, precision 0.950,
recall 0.905, Brier 0.095, ECE 0.114, $0.0027 for 50 requests. The full
write-up is `docs/status/jev-quality-benchmark-2026-10-24.md`.

The compact judge artifact for editor decks is
`data/processed/classified.json`: category/verdict counts and the top-scored
judged items. `pipeline/deck_quality.py` joins it and `judgments.json` into the
daily, weekly, Playbook, wiki, and Foundations input bundles, attaches the
judge fields, and filters known drops. The full local pool is under
`data/quality/classified/`.
