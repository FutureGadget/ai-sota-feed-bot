---
title: "Harness cost rank flips with the model, and 64.5% of spend goes to runs that fail"
date: 2026-11-17
theme: harness-and-context
evidence: [76dc46fd98b03354]
also: [agent-benchmarks, agent-orchestration]
---
FrontierHarness Eval v1.1 ran **22 harness configurations × 5 open-weight models × 62 terminal tasks × 4 attempts** (27,280 runs, 83B tokens). Each model had a different best-value harness. By cost per task the median harness moved **11 of 22 places** between models, and Codex CLI went from 1st with GLM-5.3 to 16th with Kimi-K3. Harness size did not predict cost.

**64.5%** of all spend went to runs that did not pass, and 68-82% of failed runs ended with a confident final answer rather than hitting the time limit. Audits zeroed 216 trials for reward hacking, 163 of them online lookups (vendor-reported).

For builders: re-benchmark the harness whenever you swap the model, and budget for failures that look like successes.
