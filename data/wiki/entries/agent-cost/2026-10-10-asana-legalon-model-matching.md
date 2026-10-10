---
title: "Matching model tier to task cut agent costs 65-76x in two vendor-reported case studies"
date: 2026-10-10
theme: routing
evidence: [9bf93d58cc35db99, 45d6a2b79938283a]
---
Two OpenAI customer stories report savings from picking the model per task, not from a cheaper model overall. Both figures are **vendor-reported** and from the customers' own tests.

- **Asana** made its browser agent **76x cheaper and 5x faster** in tests by moving to GPT-6 Astra in Codex.
- **LegalOn** cut estimated daily Codex costs **65%** with no loss of development speed by matching Astra, Sol, and Luna to task types and managing budgets per tier.

Neither post publishes its task mix or quality metric, so treat the ratios as upper bounds. The reusable step is the same as in [Open SWE's router](/topic/agent-cost#2026-10-02-open-swe-harness-router): measure cost per task by type, then assign tiers.
