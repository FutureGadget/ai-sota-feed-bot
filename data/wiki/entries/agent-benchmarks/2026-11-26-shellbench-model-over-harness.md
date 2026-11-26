---
title: "ShellBench: on everyday tasks, model choice moves pass rates more than harness choice"
date: 2026-11-26
theme: own-workload
evidence: [8e681754c00e3bfc]
also: [agent-orchestration]
---
ShellBench is **100** day-to-day tasks drawn from more than 10 million user requests, each in a messy workspace with competing data sources, graded for correctness and safety. The authors ran **12 models × 5 harnesses × 3 reasoning levels** (53,100 rollouts). Harness choice barely mattered: pass@1 ranged from **42.9** (Claude Code) to **45.2** (OpenClaw), with little safety difference. Among models, the top three were within **1.1 points**; GPT-6.1 Sol passed **61.4%** at about one-sixth of GPT-6 Astra's estimated token cost, against Astra's **62.5%**.

For builders: on general shell work, spend evaluation effort on model and cost per attempt before switching harnesses. Re-check on your own tasks, since 80% of the suite is held back.
