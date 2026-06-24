# Agent Builder Foundations — Schema

Foundations is the site's durable authority layer for serious agent builders.
It explains LLM and agent-system mechanisms through builder questions, with
explicit evidence tiers and practical application guidance.

The source of truth is markdown under `data/foundations/concepts/`. The
deterministic compiler `pipeline/build_foundations.py` validates those pages and
writes `data/foundations/index.json`, which is served by `/api/foundations` and
rendered into `/foundations` plus `/foundations/<slug>`.

The LLM remains disabled in the deterministic pipeline. Synthesis is performed by
the `foundations-curator` routine outside GitHub Actions.

## Audience

Assume a strong software engineer building agents. The reader can handle
mathematical reasoning, but the page should explain math as usable intuition
before notation. Do not write a generic beginner LLM course or prompt-tip list.

## Clusters

Allowed `cluster` values:

| cluster | label |
|---|---|
| `prompting` | Prompting and instruction following |
| `retrieval` | Retrieval and grounding |
| `tool-use` | Tool use and agents |
| `memory` | Memory and context |
| `evaluation` | Evals and reliability |
| `operations` | Cost, latency, and operations |
| `safety` | Safety and control |

## Page Format

Each page is YAML front matter plus markdown sections. The slug must match the
filename stem and `^[a-z0-9][a-z0-9-]{0,80}$`.

```markdown
---
slug: prompt-reliability
title: "What makes a prompt reliable?"
question: "What makes a prompt reliable?"
summary: "Reliable prompts reduce ambiguity, constrain outputs, and make failures measurable."
status: active
cluster: prompting
updated: 2026-06-25
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [agent-evaluation]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: brown-2020-language-models
    kind: theory-paper
    title: "Language Models are Few-Shot Learners"
    url: "https://arxiv.org/abs/2005.14165"
    note: "Shows few-shot demonstrations can specify tasks in context."
covers_evidence: [brown-2020-language-models]
---

## Builder consequence
What changes for an agent builder.

## Short answer
The compact answer.

## Builder model
The practical mental model.

## Mechanism
The technical explanation.

## Math intuition
Optional, but required when `math_depth: intuition`.

## Evidence
How the cited sources support the page.

## How to apply
Opinionated builder guidance.

## Failure modes
What goes wrong when the concept is misunderstood.

## Related
Optional additional cross-links.
```

Required sections:

- `Builder consequence`
- `Short answer`
- `Mechanism`
- `Evidence`
- `How to apply`
- `Failure modes`

`Math intuition` is required when `math_depth: intuition`.

## Evidence Kinds

Every material claim should be traceable to one of these tiers:

| kind | reader label | meaning |
|---|---|---|
| `theory-paper` | theory/paper-backed | Established theory or scholarly paper-backed mechanism. |
| `benchmark-result` | benchmark/result-backed | Empirical benchmark or result with clear method. |
| `production-field-report` | production field-report-backed | Engineering postmortem or measured production write-up. |
| `primary-doc` | primary-doc-backed | Official platform, model, or framework documentation. |
| `editorial-inference` | editorial inference | LLM Digest's practical synthesis; no unsupported numbers. |
| `story` | source story | Durable story `sid` already in `data/stories/index.json`. |
| `storyline` | storyline | Existing storyline slug. |

External evidence requires `id`, `kind`, `title`, and `url`, except
`editorial-inference`, which requires `id`, `kind`, `title`, and `note`.
`story` evidence requires `sid`. `storyline` evidence requires `slug`.

## Invariants

1. Slugs are valid, unique, and match filenames.
2. Clusters are known.
3. Required sections exist.
4. Evidence kinds are known.
5. `story` evidence resolves in `data/stories/index.json`.
6. `storyline` evidence and `related_storylines` resolve in
   `data/storylines/index.json` when that index exists.
7. `related_topics` resolve in `data/wiki/index.json` when that index exists.
8. The compiled output is deterministic except for `generated_at`.
