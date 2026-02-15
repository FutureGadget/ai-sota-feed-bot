# LLM Ranking (v2.0)

## Objective
Improve candidate quality by adding semantic labeling before final ranking.

## Phase A behavior
- For each eligible candidate, produce labels:
  - platform_relevant (bool)
  - novelty (1-5)
  - practicality (1-5)
  - hype (1-5)
  - why_1line
- Cache labels by item id to avoid repeated calls.
- If LLM is unavailable, use deterministic heuristic labels.
