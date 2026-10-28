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
- **Release significance:** the deterministic tier in
  `pipeline/release_policy.py` ranks substantive releases (a changelog with
  real features/fixes, a first-party open-weight drop, or an X.0.0 version)
  above bare bumps, dependency updates, prereleases, and generic notes inside
  the Releases lane. The default Brief excludes every release item, and the
  tier is not a judge verdict.
- **Community-only windows:** the API community caps are 4 and the community
  slot allows 3 cards from one source, matching the slot's 4-item lane. A
  quiet day whose only fresh source is Hacker News shows the day's best
  discussion instead of being truncated to two cards.
- **Precision@10:** on a small human-labeled sample, the share of cards a staff
  platform engineer would call useful or must-read.

Reader CTR is a guardrail, not the objective. A clickbait card can win CTR
while losing the finishable, anti-hype product promise.

The offline Jev/decision-model benchmark and review workflow live in
`docs/how-to/jev-quality-benchmark.md`. Recap selection (a fixed-budget pick,
where F1 hides the precision/recall trade-off) is scored with must-cover
recall@K and alpha-nDCG@K against owner grades:
`docs/how-to/deck-selector-benchmark.md`.

## Jev semantic gate (2026-10-24, recalibrated 2026-10-26)

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
- **the judge needs evidence**: items below
  `content_fetch.min_evidence_chars` (300, releases exempt) stay `unjudged`
  with `judge_error: insufficient_evidence` and pass the headroom floor. The
  deterministic policy decides instead of a snippet-driven low score. This is
  what keeps search results (Google News gives ~76 characters) and failed
  content fetches from being scored as junk.
- prior judgments are reused from `data/processed/judgments.json`; the key
  includes an evidence bucket (`judge_evidence_chars`), so a snippet-only
  judgment is refreshed once the article body is available. Only new,
  changed, or thin-evidence candidates call Jev.

Offline benchmark (v2, 2026-10-26): AUC 1.000, F1 1.000 at 0.35, precision
1.000, recall 1.000, Brier 0.024, ECE 0.112, 50 requests. The v1 baseline was
AUC 0.969 / F1 0.927 at 0.25 / Brier 0.095. Peak scores are partly in-sample:
the v2 rubric examples were adjusted on this same 50-item sample, so relabel a
fresh week before treating them as general. Write-ups:
`docs/status/jev-quality-recalibration-2026-10-26.md` and
`docs/status/jev-quality-benchmark-2026-10-24.md`.

The compact judge artifact for editor decks is
`data/processed/classified.json`: category/verdict counts and the top-scored
judged items. `pipeline/deck_quality.py` joins it and `judgments.json` into the
daily, weekly, Playbook, wiki, and Foundations input bundles, attaches the
judge fields, and filters known drops. The full local pool is under
`data/quality/classified/`.
