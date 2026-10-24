# Jev quality benchmark, 2026-10-24

First end-to-end runs of the offline benchmark against Jev 1.14 through
OpenRouter's System One API. Labels are assistant-authored and provisional;
the review packet is the next step, not a verdict on the labels themselves.

## Setup

- Model: `jev-1.14` via `POST https://openrouter.ai/api/v1/systemone`
- Sample: 50 items, 21 `keep` / 29 `drop`, 8 slices
- Input: title, source, source role, published date, URL, 2,500-character
  body excerpt
- Run A (single question): one `keep` question with the full rubric.
- Run B (hybrid): four questions in one request:
  - `keep`: the holistic "does this belong in the default Brief?" question
  - `platform_relevant`: platform/agent engineering rather than a domain
    application or general AI news
  - `release_lane`: a routine release note or bare version bump that belongs
    in the Releases tab
  - `corporate_marketing`: a marketing or corporate announcement without a
    concrete engineering or distribution change
- Hybrid policy: `keep` is the primary score; `release_lane >= 0.6`,
  `corporate_marketing >= 0.7`, or `platform_relevant < 0.35` clamps the
  score to 0.1. The auxiliary questions are gates, not a product.
- Cost: single-question 55,565 input tokens, 1,000 output, $0.0023;
  hybrid 63,165 input tokens, 3,800 output, $0.0027.
- Latency: 442 ms average single-question, 437 ms average hybrid; 651 ms max.

## Results

| metric | Hybrid Jev | Single-question Jev | heuristic baseline |
|---|---:|---:|---:|
| AUC | **0.969** | 0.965 | 0.871 |
| F1 at tuned threshold | **0.927** (0.25) | 0.878 (0.25) | 0.829 (0.60) |
| precision | **0.950** | 0.900 | 0.850 |
| recall | **0.905** | 0.857 | 0.809 |
| Brier | **0.095** | 0.100 | 0.160 |
| ECE(10) | 0.114 | **0.106** | 0.215 |

At the default 0.50 threshold the hybrid is precision-first: precision 0.933,
recall 0.667, F1 0.778. The tuned 0.25 threshold is the useful operating point
on this sample.

The heuristic baseline is not independent: the labels were authored by the
assistant and may share its source/title priors. Treat the baseline as a
floor, not a gold standard.

## Slice notes (hybrid)

- `first_party_engineering`: 1.000 F1. Paragraph-level excerpt extraction
  fixed the earlier Cloudflare/Anthropic misses.
- `releases`: 1.000 F1. The `release_lane` gate drops routine release notes
  even when their changelogs are technical; the two substantive first-party
  release posts are kept.
- `practitioner_analysis`: 1.000 F1.
- `search_business_gossip`: 1.000 F1.
- `research`: 0.909 F1. One false positive: a low-resource Bashkir
  adaptation paper that is rigorous but not platform/agent engineering.
- `first_party_marketing`: precision 1.000, recall 0.500. No marketing false
  positives; one hard-positive distribution announcement was dropped.
- `off_topic_domain`: no true positives by construction; one false positive
  remains (the Bashkir paper).
- `search_seo`: 0 F1. The one genuine search scoop is title-only from a
  low-authority publisher and scored 0.04. A title plus publisher is not
  enough for a semantic judge.

## Remaining review cases

- **False positive:** Bashkir adaptation paper, score 0.51. `platform_relevant`
  was 0.92 and `keep` 0.51. This is a label/spec borderline: it is rigorous
  ML research, but not platform/agent engineering.
- **False negative:** DeepSeek search scoop, score 0.04. Title-only input.
  This is a data limitation, not a model verdict.
- **False negative:** OpenAI models on Google Cloud, score 0.12. A
  distribution announcement that changes where platform teams can run the
  model. The holistic `keep` question treats it as a partnership post; adding
  a hard-positive example would help.

## What this means

Jev 1.14 with the hybrid gate is a credible coarse quality gate:

- cheap and fast enough to score every candidate;
- strong calibration (Brier 0.095) and the best F1/AUC of the three
  approaches;
- perfect on first-party engineering, practitioner analysis, releases, and
  search business/gossip;
- no marketing false positives at the tuned threshold.

It is still not a sole curator:

- title-only search results are not judgeable; keep the deterministic search
  quarantine or enrich the publisher body;
- one niche research false positive remains;
- a distribution announcement can be mistaken for marketing;
- the labels need owner review before the numbers are treated as ground
  truth.

## Next

1. Owner review of the 50 labels, especially the marketing and research
   borderline cases.
2. Add a hard-positive example for distribution/availability announcements
   and a stricter off-mission rule for applied NLP research.
3. Enrich search results with the publisher's body where possible, or keep
   search out of the semantic gate.
4. Re-run the benchmark and compare against this hybrid baseline before
   shadow mode.
