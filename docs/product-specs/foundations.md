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

Each concept page has two parts.

**The explanation** starts from a builder consequence and works downward, with
each section word-capped by `pipeline/build_foundations.py`:

1. Builder consequence (≤80 words)
2. Short answer (≤120)
3. Builder model (≤200, optional)
4. Mechanism (≤350)
5. Math intuition (≤200, when useful)
6. How to apply (≤250)
7. Failure modes (≤150)
8. Related links (≤60, optional)

**The evidence list** holds at most 12 sources. Each has the date it was filed
(`added`) and a note of at most 80 words saying what it shows. Study-by-study
detail lives only there; the explanation names a study once, with its key
number. A source that arrived through a feed story carries that story's `sid`,
so one entry links both the primary source and its `/story` permalink.

Explanation must be careful and source-grounded. Application guidance should be
opinionated: what to do, what to test, and what mistake to avoid.

### Reading surfaces (2026-10-06)

- Concept page: lead, cross-links, **What's new in the evidence** (the three
  newest sources, dated, deep-linking into the list), the explanation, then the
  evidence list newest first with tier, date, note, and an "in the feed" link.
- `/foundations`: a **Recently added evidence** list (newest external sources
  across concepts) above the clusters; each concept card shows its source count
  and last update.

New concepts and updates follow the same contract: the curator adds dated
evidence and rewrites sections within their caps, and the build rejects pages
that don't comply.

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
