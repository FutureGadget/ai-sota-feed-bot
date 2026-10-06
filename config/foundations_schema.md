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

A page has two parts with different jobs:

- **The explanation** (the sections): a durable, bounded answer to the
  builder question. It names patterns and, at most, cites a study by name with
  its key number. It is rewritten when understanding changes, never appended
  to.
- **The evidence list** (front matter): every source, each with the date it was
  filed (`added`) and a short note saying what it shows. Study-by-study detail
  lives here and nowhere else. New findings arrive as new evidence entries.

```markdown
---
slug: prompt-reliability
title: "What makes a prompt reliable?"
question: "What makes a prompt reliable?"
summary: "Reliable prompts reduce ambiguity, constrain outputs, and make failures measurable."   # <= 45 words
status: active
cluster: prompting
updated: 2026-06-25          # last edit to the explanation
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [agent-evaluation]
related_playbook_cards: []
related_storylines: []
evidence:                    # 1-12 entries
  - id: brown-2020-language-models
    kind: theory-paper
    title: "Language Models are Few-Shot Learners"
    url: "https://arxiv.org/abs/2005.14165"
    sid: "00678eb9b30563c3"  # optional: the feed story it arrived through
    added: 2026-06-25        # date filed into this page
    note: "Shows few-shot demonstrations can specify tasks in context."   # <= 80 words
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

## How to apply
Opinionated builder guidance.

## Failure modes
What goes wrong when the concept is misunderstood.

## Related
Optional additional cross-links.
```

### Sections (enforced)

| section | required | max words |
|---|---|---|
| `Builder consequence` | yes | 80 |
| `Short answer` | yes | 120 |
| `Builder model` | no | 200 |
| `Mechanism` | yes | 350 |
| `Math intuition` | when `math_depth: intuition` | 200 |
| `How to apply` | yes | 250 |
| `Failure modes` | yes | 150 |
| `Related` | no | 60 |

No other sections are allowed. There is no `Evidence` section: the rendered
page lists the evidence entries, newest first, with their notes and dates.

### Evidence entries (enforced)

- 1-12 entries per page, unique `id`s. At 12, retire the weakest or a
  superseded entry before adding one.
- `added: YYYY-MM-DD` on every entry: the date it was filed into this page.
  Never change it on an existing entry.
- `note` <= 80 words: what the source shows, with its key number. Required for
  external evidence and `editorial-inference`.
- When a paper, doc, or report arrived through a feed story, put the story's
  `sid` on that entry instead of adding a separate `story` entry.

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

External evidence requires `id`, `kind`, `title`, `url`, `added`, and `note`;
`editorial-inference` requires `id`, `kind`, `title`, `added`, and `note`.
`story` evidence requires `sid`; `storyline` evidence requires `slug`.

## Invariants

`pipeline/build_foundations.py` reports every violation at once and exits
non-zero with `FOUNDATIONS_BUILD_FAIL …`; `--slug <slug>` limits the report to
one concept.

1. Slugs are valid, unique, and match filenames.
2. Clusters are known; `summary` is at most 45 words.
3. Only the allowed sections appear, each within its word cap; required
   sections exist; `Math intuition` exists when `math_depth: intuition`.
4. Evidence: 1-12 entries, known kinds, unique ids, a valid `added` date on
   each, notes within 80 words, and the per-kind required fields.
5. Every `sid` (on `story` evidence or external evidence) resolves in
   `data/stories/index.json`.
6. `storyline` evidence and `related_storylines` resolve in
   `data/storylines/index.json` when that index exists.
7. `related_topics` resolve in `data/wiki/index.json` when that index exists.
8. The compiled output is deterministic except for `generated_at`. Each
   concept's evidence is ordered newest `added` first; its `updated` is the
   later of the page's `updated` and its newest evidence; the index carries
   `recent_evidence` (the newest external evidence across all concepts).
