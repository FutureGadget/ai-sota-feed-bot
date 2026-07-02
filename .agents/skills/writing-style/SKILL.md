---
name: writing-style
description: Shared prose-quality bar for every reader-facing editorial skill (daily-summary, weekly-summary, storyline-editor, wiki-curator, playbook, foundations-curator). Four principles — BLUF, one idea per paragraph, scannability, specifics over generalities — plus the cut-test for a final edit pass. Read this before writing intros, summaries, highlights, category blurbs, narrative fields, wiki prose, or Playbook cards.
---

This is not a standalone routine — it has no scripts, no input bundle, and
nothing to publish. It is the shared style contract the other editorial
skills reference before they write prose. If a skill's own guidance and this
file conflict on formatting, the skill's guidance wins (it knows its field
constraints); on everything else, follow this file.

The reader is a busy platform/agent engineer deciding in seconds whether a
piece is worth their time (see `AGENTS.md` → Product Positioning). These four
principles exist to respect that.

## 1. BLUF (Bottom Line Up Front)

State the main takeaway, conclusion, or core thesis in the first sentence or
two. Never open with throat-clearing, historical background, or scene-setting
before the point.

- A daily/weekly `intro` leads with what actually happened, not "This week saw
  continued developments in AI."
- A storyline `whats_new` leads with the newest consequential fact, not a
  recap of the launch.
- A wiki "State of the art" section leads with the current answer, not the
  history of the obstacle.
- A Playbook `problem` states what hurts today, not context about the field.

## 2. One idea per paragraph

Every paragraph (or, for single-sentence fields, every sentence) carries one
focus. The moment the thought pivots — a new angle, a caveat, a different
example — start a new paragraph or sentence instead of joining it with
"however," "additionally," or a comma splice.

- If a recap `intro` paragraph needs "However" or "Additionally" mid-sentence
  to hold together, split it.
- A category `summary` makes one pattern claim, not two unrelated ones stapled
  together.
- A storyline `beat` covers one phase of the arc, not the whole story
  compressed into one node.

## 3. Prioritize scannability

Assume the reader skims before they read. Structure output so the shape of
the content — not just its words — carries the meaning.

- Use the structured fields these skills already provide as scan aids:
  `highlights` bullets, category `name`/`summary` headers, Playbook's
  `SIGNAL → APPLY → EXPECTED` card spine, storyline `beats` and `status`.
  These exist precisely so a reader gets the gist without reading every word —
  don't let them go slack (vague names, filler bullets).
- Keep list items and bullets to one line each. If a "one-liner" needs a
  semicolon to fit everything, it's two bullets.
- In markdown pages (wiki, Foundations), use descriptive bold headers and
  bullet/numbered lists for anything sequential or enumerable, not a wall of
  prose paragraphs.
- Bold sparingly, only on the phrase or figure that should catch a skimmer's
  eye — bolding half a paragraph defeats the purpose.

## 4. Specifics over generalities

Replace abstract claims and weak modifiers ("very," "significantly,"
"efficient," "a lot") with a concrete detail, number, or mechanism.

- Weak: "This makes agent workflows much faster."
  Specific: "This cuts the tool-call round trip from 3 calls to 1."
- Only state a number when the cited source actually supports it — see each
  skill's evidence rules (Playbook's `evidence.kind`, Foundations' evidence
  tiers, wiki's `evidence` sids). Never invent a figure to sound concrete;
  an honest qualitative claim beats a fabricated number.
- Name the actual mechanism, model, benchmark, or company instead of "a major
  AI company" or "a new technique."

## The cut test (final pass)

Before saving, read every sentence and ask: **if I delete this, does the
reader lose critical information?** If no, cut it. This is what keeps an
`intro` to 2–3 short paragraphs, a `tldr` to two sentences, a Playbook
`problem`/`result` to one or two tight lines — the fields these skills cap in
characters are capped for this reason, not arbitrarily. Lean, specific
writing wins; do not pad a field just to fill its budget.
