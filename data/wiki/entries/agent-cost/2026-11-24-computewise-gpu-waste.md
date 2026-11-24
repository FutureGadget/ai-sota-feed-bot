---
title: "Unaided research agents spent only 52% of GPU time on needed work; a harness removed 80% of the excess"
date: 2026-11-24
theme: harness-and-context
evidence: [65ec3990fe35471d]
also: [agent-benchmarks]
---
*ComputeWise* is an open benchmark with a simulated GPU that measures how much compute AI research agents waste on redundant runs, idle allocation, and jobs they never read the results of. Unaided agents spent **52%** of GPU time on necessary work. An open-source harness removed over **80%** of the extra time across five models.

For builders: for agents that launch jobs, compute is a bigger bill than tokens. Meter GPU time per agent task and enforce job-level checks in the harness, such as no duplicate launches and no idle reservations.
