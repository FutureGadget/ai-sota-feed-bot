# Jev quality benchmark, 2026-10-24

First end-to-end run of the offline benchmark against Jev 1.14 through
OpenRouter's System One API. Labels are assistant-authored and provisional;
the review packet is the next step, not a verdict on the labels themselves.

## Setup

- Model: `jev-1.14` via `POST https://openrouter.ai/api/v1/systemone`
- Task: one `noul` question, `keep`, "Does this item belong in the default
  Brief for AI platform and agent engineers?"
- Sample: 50 items, 21 `keep` / 29 `drop`, 8 slices
- Input: title, source, source role, published date, URL, 2,500-character
  body excerpt
- Prompt: `feed-quality-v1` in `config/judge.yaml`, including the
  `Source role: release` rule and the domain-science rule
- Cost: 55,565 input tokens, 1,000 output tokens, **$0.0023 total**
- Latency: 442 ms average, 614 ms max for the 50 requests

## Results

| metric | Jev 1.14 | heuristic baseline |
|---|---:|---:|
| AUC | **0.965** | 0.871 |
| F1 at tuned threshold | **0.878** (0.25) | 0.829 (0.60) |
| precision | **0.900** | 0.850 |
| recall | **0.857** | 0.809 |
| Brier | **0.100** | 0.160 |
| ECE(10) | **0.106** | 0.215 |

At the default 0.50 threshold Jev is precision-first: precision 0.938,
recall 0.714, F1 0.811. The tuned 0.25 threshold trades precision for recall.

The heuristic baseline is not independent: the labels were authored by the
assistant and may share its source/title priors. Treat the baseline as a
floor, not a gold standard.

## Slice notes

- `first_party_engineering`: 1.000 F1. The paragraph-level excerpt extraction
  fixed the earlier Cloudflare/Anthropic misses.
- `releases`: 1.000 F1 after adding the `Source role: release` rule. Routine
  release notes are now dropped even when their changelogs are technical;
  the two substantive first-party release posts are kept.
- `search_business_gossip`: 1.000 F1.
- `practitioner_analysis`: 0.857 F1. One false negative on a title-only
  InfoQ item whose fetched excerpt was mostly navigation.
- `research`: 0.909 F1. One false positive: a low-resource Bashkir
  adaptation paper that is rigorous but not platform/agent engineering.
- `first_party_marketing`: 0.500 F1. The model kept the relevant Agent Skills
  donation and a hard positive, but also kept a funding post with a usage
  datapoint, and dropped the OpenAI-on-Google-Cloud distribution announcement.
- `off_topic_domain`: no true positives by construction. Jev still kept
  clinical, biology, and protein-deployment items at the 0.25 threshold; the
  domain rule is better than before but not sufficient.
- `search_seo`: 0 F1. The one genuine search scoop was title-only from a
  low-authority publisher and scored 0.04; comparison listicles scored higher.
  A title plus publisher is not enough for a semantic judge.

## What this means

Jev 1.14 is promising as a **coarse gate**:

- cheap and fast enough to score every candidate;
- strongly calibrated on this sample (Brier 0.100, ECE 0.106);
- perfect on first-party engineering and routine releases after the source-role
  rule;
- beats the deterministic heuristic baseline on every headline metric.

It is not ready to be the sole curator:

- search results need body enrichment or should stay with the deterministic
  search quarantine;
- off-mission domain science needs a separate relevance question or stronger
  examples;
- marketing/distribution announcements need their own decision axis;
- the single probability forces a precision/recall tradeoff that a
  multi-question request could split into interpretable signals.

## Next

1. Owner review of the 50 labels, especially the marketing and research
   borderline cases.
2. Add a multi-question System One request:
   `substantive`, `platform_relevant`, `release_lane` (and optionally
   `corporate_marketing`). Combine them with an explicit policy instead of one
   binary score.
3. Enrich search results with the publisher's body where possible, or keep
   search out of the semantic gate.
4. Re-run the benchmark and compare against this baseline before shadow mode.
