---
title: "GameLogicBench checks game rules at every tick, not just the end state"
date: 2026-09-23
theme: coding-benchmarks
evidence: [77a5eee1e1f2521e]
---
A game can end in a valid state after breaking its rules mid-run. **GameLogicBench** evaluates coding agents implementing gameplay rules with **tick-level state assertions** throughout execution, instead of replaying fixed examples, scoring videos, or asking a model to judge.

Same lesson as trajectory grading for agents: checking only the end state misses failures along the way.
