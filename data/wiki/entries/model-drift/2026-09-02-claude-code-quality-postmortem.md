---
title: "Anthropic traces weeks of Claude Code quality complaints to three silent default and prompt changes"
date: 2026-09-02
theme: model-and-default-changes
evidence: [85b0ca3c45b5c993]
---
Anthropic's postmortem on complaints from March 4 to April 20, 2026 finds three un-flagged changes, none touching a pinned model or SDK version:

- default reasoning effort cut from `high` to `medium` for latency (reverted)
- a caching bug misusing `clear_thinking_20251015` that **cleared reasoning every turn**, fixed in v2.1.101 and masked by two concurrent changes
- a "≤25 words between tool calls" prompt line that cost **3% on broader evals**

Remediation: per-model evals and ablations before prompt or default changes, soak periods, gradual rollouts, and dogfooding public builds. Pinning would not have caught any of it.
