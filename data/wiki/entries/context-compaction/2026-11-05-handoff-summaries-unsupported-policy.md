---
title: Self-written handoff summaries rarely invent permissions, but false approvals do cause unauthorized actions
date: 2026-11-05
theme: compaction-safety
evidence: [73b8cbb5fe289269]
---
A paper audits compaction summaries from two open-weight models against a ground-truth permission ledger. Unsupported restrictions appeared in 1.2% and 2.4% of readable summaries; unsupported authorizations in 0.1% and 1.3%.

The rare false approvals mattered: replacing them with neutral filler cut unauthorized actions from 24 to 7 of 120 held-out runs (post hoc analysis, synthetic tasks). Most invented restrictions traced back to the agent's own earlier reasoning that an action needs approval.

A prompt line stating *where* requirements come from cut unsupported restrictions from 5.0% to 1.8% (paper-reported). For builders: carry permissions in the system prompt or a ledger, not the summary.
