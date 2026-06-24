# Agent Builder Foundations

## Job

Foundations is the authority layer for LLM Digest as an agent-builder portal. It
explains the mechanisms behind agent-building practice so a serious builder can
trust the site beyond the daily feed.

The section answers builder questions such as:

- What makes a prompt reliable?
- Why does adding more context sometimes hurt?
- When should I use RAG instead of fine-tuning?
- What should an agent eval measure?
- Why do tool-calling agents make weird mistakes?

## Audience

Strong software engineers building agents. Readers may have high mathematical
capacity, but they should not need to be ML researchers. Pages explain math as
usable intuition before notation.

## Page Contract

Each concept page starts from a builder consequence, then works downward:

1. Builder consequence
2. Short answer
3. Builder model
4. Mechanism
5. Math intuition, when useful
6. Evidence
7. How to apply
8. Failure modes
9. Related links

Explanation must be careful and source-grounded. Application guidance should be
opinionated: what to do, what to test, and what mistake to avoid.

## Evidence Tiers

Claims are labeled by evidence tier:

- `theory-paper`
- `benchmark-result`
- `production-field-report`
- `primary-doc`
- `editorial-inference`
- `story`
- `storyline`

The schema in `config/foundations_schema.md` is authoritative. Unsupported
numbers are not allowed; editorial inference must be labeled.

## Relationship to Existing Surfaces

- Feed, Daily, Weekly: what changed.
- Storylines: what is evolving over time.
- Playbook: what to apply.
- Map: what problem/solution graph the builder is navigating.
- Foundations: why the underlying mechanism behaves that way.

Foundations links to `/map`, `/playbook`, storylines, and stories, but its
source of truth is `data/foundations/concepts/*.md`.

## Non-goals

- Generic beginner LLM course.
- Prompt-tip listicles.
- Comments, community profiles, agent cards, or agent shop in the first release.
- Re-enabling LLM calls inside the deterministic pipeline.

## First Release

Ship `/foundations` and `/foundations/prompt-reliability`.

Success means a strong engineer can read the first page, trust the evidence,
explain the mechanism to someone else, and name one concrete prompt or
agent-design improvement.
