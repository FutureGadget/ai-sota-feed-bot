---
title: "Grafana turns agent behaviour into SLOs with error budgets"
date: 2026-10-16
theme: monitoring-limits
evidence: [d771557f3f2a708f]
also: [agent-evaluation]
---
Latency, error rate, and token counts say nothing about whether an answer was grounded or useful. Grafana proposes running **evaluations** per interaction (grounded, request fulfilled, toxic, PII exposed, injected) and treating each result as an SLI. Checks can be an LLM judge or deterministic rules such as regexes.

Each behaviour gets its own objective instead of one "quality score". Example: 95% of conversations judged fulfilled over 30 days; the other 5% is the error budget. While budget remains, teams can change prompts or models. Once it burns, effort shifts to quality.

For builders, budget burn surfaces slow drift (a prompt, model, or retrieval change costing a fraction of a point per day) that error-rate alerts miss. Grafana-described proposal, not a measured result.
