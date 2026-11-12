---
title: "A task-bound monitor admitted 1.3-7.7% of attack calls that the model proposed 64-84% of the time"
date: 2026-11-12
theme: harness-controls
evidence: [54f1f65b7c731a1b]
also: [agent-sandboxing]
---
A paper compares in-prompt defences with deterministic enforcement outside the model, across 13 tasks and 12 tools with an effect-based oracle. Qwen2.5-1.5B and 7B proposed the attacker's call in 64% and 84% of 156 attack episodes; a task-bound reference monitor admitted 1.3% and 7.7%.

Prompt guardrails were model-dependent: a hardened prompt moved obedience from 67% to 65% on one model and 86% to 55% on the other.

Monitor quality matters. A naive monitor admitted 18 of 33 effective attack variants, a hardened one 6, a capability-bound one 1.

Limits the authors state: two small open-weights models, static attacks only, and the human-approval and taint-tracking results are simulation-only. In that simulation, approval without a deterministic per-episode budget fails to approval spamming.
