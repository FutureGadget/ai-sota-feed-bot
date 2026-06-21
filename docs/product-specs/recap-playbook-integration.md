# Recap Playbook integration

Daily and weekly recaps may show a compact **Playbook takeaway** below an
article when the regular Playbook agent produced a validated card for that
exact source.

## Product contract

- Playbook is the canonical editorial source for `problem → apply → result`.
- Recap agents summarize and categorize news; they never duplicate those fields.
- Matching is exact and deterministic through
  `sid = sha256(normalized source_url)[:16]`. Titles are never matched.
- Weekly recaps show at most five takeaways; daily recaps show at most three.
- Missing, invalid, or unmatched Playbook data leaves the recap unchanged.
- `/playbook` remains the complete action archive.

## Card kinds

`source-backed` cards are eligible for recap embedding and require:

- stable `id`
- exact `source_url` copied from the input bundle
- matching `source_sid`
- `problem`, `apply`, and `result`
- `evidence.kind` and `evidence.note`

`evergreen` cards represent durable wiki guidance. They require `topic_url`,
remain visible on `/playbook`, and are not eligible for recap embedding unless
a future agent run creates a separate source-backed card.

## Evidence semantics

- `source-measured`: the primary source reports a measured result.
- `source-claimed`: a vendor or project claims the result. The UI labels it
  `Source claim`.
- `editorial-inference`: a qualitative expected outcome. Inferred results may
  not contain unsupported percentages, multipliers, latency figures, benchmark
  scores, or guarantees.

## Routine order

```text
build Playbook input
→ agent writes Playbook edition
→ validate and build source-index.json
→ build recap input
→ agent writes recap
→ render recap with source-card overlay
```

Weekly input includes news, releases, research, and papers so actionable
engineering work can support the weekly narrative. Daily remains news-first.

## Rendering

The inline block uses the Playbook hierarchy:

1. Problem
2. Apply — visually dominant
3. Expected
4. Evidence label and guide link

The article title continues to link to the original source. The guide link uses
the related `/topic/<slug>` page when present, otherwise the canonical Playbook
edition.
