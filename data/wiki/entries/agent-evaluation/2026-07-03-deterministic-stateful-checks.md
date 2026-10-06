---
title: "Stateful agents can be checked on state transitions without an LLM judge"
date: 2026-07-03
theme: grading-trajectories
evidence: [5d87a279aac331cb]
---
A deterministic-replacement approach for **stateful agent evaluation** checks state transitions directly instead of asking a model to grade them.

"Judge with another LLM" is a default, not a requirement. Where the task admits a programmatic check, skipping the judge removes its cost, bias, and non-determinism at once.
