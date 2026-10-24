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
