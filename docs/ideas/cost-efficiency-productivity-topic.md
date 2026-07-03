# Cost Efficiency & Productivity Coverage Lens

## Problem Statement

How might we make **cost efficiency and productivity** a visible, first-class
topic on llm-digest.com — the "does this agent pay for itself, and how do I
make it cheaper per task" job our readers increasingly own — without breaking
the anti-hype positioning that deliberately filters out the enterprise
"AI productivity/ROI" marketing genre?

Companies are converging on productivity as the justification for AI spend,
and for the engineers we serve that pressure lands as concrete work:
cost-per-task accounting, model downshift economics, caching strategy, and
proving time savings with evidence instead of vendor claims.

## What already exists (do not rebuild)

- **Wiki:** `cost` and `latency` are existing obstacle areas. `/topic/agent-cost`
  is one of the richest pages on the site, cross-linked to `cost-controls`,
  `context-compaction`, and `agent-orchestration`. Cost *reduction* is well
  covered; cost/productivity *measurement and proof* is not.
- **Ranking:** `config/profile.yaml` `platform_keywords` already includes
  `cost`, `optimization`, `latency`, `throughput`, so cost-efficiency content
  from existing sources already scores as platform-relevant.
  `config/ranking.yaml` `topical_bias.positive_keywords` has no efficiency
  terms — a possible (deliberate, separate) micro-tune.
- **Preferences:** `config/user_preferences.yaml` lists "developer
  productivity" as a priority already.
- **Guardrails that must survive:** `hype_keywords` excludes "case study" /
  "customer story"; `off_topic.policy_economics_governance` drops
  macro-productivity content ("labor market", "economic index"). These filters
  are what keep the enterprise-ROI genre out, and they stay untouched.

## Recommended Direction

Treat this as an **editorial lens over existing machinery**, not a new
surface. Smallest shippable first:

1. **Wiki obstacle page (core move).** Add one obstacle page in the *existing*
   `cost` area — working slug `proving-agent-roi` — for the measurement half
   of the problem: "it's hard to prove an agent actually saves time and
   money." Covers cost-per-task accounting, downshift economics (per-token
   price vs. total tokens spent), productivity measurement methodology, and
   the evidence bar for ROI claims. No schema change; cross-links to
   `cost-controls` and `agent-cost`; the `wiki-curator` routine writes it with
   real evidence sids through the normal ingest path.
2. **Playbook emphasis.** Cost-efficiency wins are the ideal Playbook card
   shape (problem → apply → result with a number: "prompt-cached the agent
   loop's stable prefix, −80% token cost"). Nudge the `playbook` skill's
   selection guidance to favor cards with a measured cost or time delta.
3. **Foundations concept (later).** An evidence-tiered "cost-efficiency
   levers for agent systems" concept page once 1–2 prove reader interest.
4. **Ranking micro-tune (optional, separate change).** If coverage feels thin
   after 1–2, add precise multi-word anchors ("cost per task", "token
   efficiency", "prompt caching") to `topical_bias.positive_keywords` —
   following the audience-widening precedent that copy/editorial changes ship
   first and ranking re-tunes are deliberate, separate decisions.

## Key Assumptions to Validate

- [ ] Readers engage more with cost/productivity-framed items — compare CTR
      (`data/feedback/ctr_clicks.json`) and `/topic/agent-cost` page views
      against other wiki nodes before investing past step 1.
- [ ] The measurement/ROI angle has enough source flow to keep a wiki page
      fresh — the curator should find new evidence sids at least every
      2–3 weeks; a stale page argues for folding it back into `agent-cost`.
- [ ] The lens can be covered without admitting the marketing genre — watch
      whether candidate evidence keeps tripping `hype_keywords`; if the only
      available sources are vendor case studies, the topic isn't ours to cover.
- [ ] It moves the north star — judge against weekly returning readers
      (`docs/status/north-star-metric.md`), not clicks alone.

## MVP Scope

- One new wiki obstacle page (`proving-agent-roi`, area `cost`) written by the
  `wiki-curator` routine, validated by `build_wiki.py` as usual.
- One line of selection guidance in the `playbook` skill favoring cards with
  measured cost/time deltas.
- No new nav entry, no new page type, no ranking change, no schema change.

## Not Doing (and Why)

- **A "productivity" ranking keyword** — a loose single word is a magnet for
  exactly the marketing content the profile excludes; precision-first rules
  (multi-word anchors only) apply if ranking is ever touched.
- **Enterprise AI-ROI thinkpieces and vendor customer stories** — already
  excluded by `hype_keywords`; the widened audience explicitly excludes
  general AI-news readers.
- **Macro/economy productivity coverage** — `off_topic.
  policy_economics_governance` exists precisely to drop this.
- **A new wiki area** — `cost` already carries the theme; adding an area is a
  schema change that should wait until pages accumulate beyond it.
- **A new site section** — storylines and recaps remain the growth artifacts;
  this is a lens inside existing surfaces.

## Open Questions

- Is one obstacle page enough, or does the measurement problem split
  (cost-per-task accounting vs. productivity-evidence methodology) once the
  curator starts writing?
- Should the daily/weekly recap agents get a standing nudge to call out
  measured cost/productivity deltas when present, the way Playbook overlays
  work today?
- Where is the line for "efficiency" research (quantization, speculative
  decoding) between the existing `latency` pages and this cost lens — does
  the wiki need clearer cross-linking guidance instead of new pages?
