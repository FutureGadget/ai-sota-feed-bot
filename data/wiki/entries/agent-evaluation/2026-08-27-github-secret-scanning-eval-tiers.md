---
title: "GitHub evaluates an LLM for secret scanning with a recall guardrail it cannot trade away"
date: 2026-08-27
theme: eval-in-production
evidence: [30f2948e24a89119]
also: [llm-as-judge]
---
GitHub's pre-production evaluation of an LLM for secret scanning uses three metric tiers: primary outcome (false-positive reduction, precision), a **safety constraint** (recall), and operational guardrails (latency, cost, reliability). A change that cuts false positives but lowers recall does not count.

Prompt, model, dataset, and config were versioned together. An LLM judge auto-cleared confident cases; low-confidence, conflicting, or high-impact cases went to humans. The **95% offline false-positive reduction** was treated as license for online experiments, not proof of production behavior.
