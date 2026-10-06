---
title: "For stateful agents, check state transitions instead of asking a judge"
date: 2026-07-03
theme: trusting-the-judge
evidence: [5d87a279aac331cb]
---
A deterministic-replacement approach for **stateful** agent evaluation checks state transitions directly instead of asking a model to grade them.

When the task admits a programmatic check, skipping the judge removes its bias, cost, and non-determinism at once. Treat LLM-as-judge as the fallback for open-ended outputs, not the default.
