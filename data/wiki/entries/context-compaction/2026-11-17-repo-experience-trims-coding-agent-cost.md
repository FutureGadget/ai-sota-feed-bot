---
title: "Learning from past sessions in a repo cut coding-agent cost 18-31% without touching the agent"
date: 2026-11-17
theme: curating-the-working-set
evidence: [60d6d445e0dacc9d]
also: [agent-cost]
---
Microsoft Research and UC Berkeley profiled Claude Code on 60 SWE-Bench tasks run in sequence per repository. Three wastes recurred: **30%** of tool calls repeated an action from an earlier task in the same repo, **16 of 23** tool descriptions sent every turn were never called, and the **17%** of tasks that failed took **32%** of spend.

TokenEconomizer, an open-source plugin, turns finished sessions into guidance for the next ones. Across 277 bug-fixing tasks it cut cost **18.4-30.9%** across several coding agents with broadly stable success. Fixed-strategy cost plugins helped in some repos and hurt in others.

For builders: per-repo memory of what worked, and which tools go unused, is a black-box cost lever that needs no model or harness change.
