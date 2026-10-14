---
title: "Harness changes alone lifted LangChain's coding agent from 52.8% to 66.5% on Terminal Bench 2.0"
date: 2026-10-14
theme: verify-and-replan
evidence: [2e12fd56c15d4708]
also: [agent-reliability, agent-tracing]
---
With the model fixed (gpt-5.2-codex), LangChain reports (**vendor-reported**) a 13.7-point gain on Terminal Bench 2.0 from harness edits alone.

- **Self-verification:** a middleware blocks exit until the agent runs a verification pass against the task spec; before, it often wrote code, reread it, and stopped.
- **Loop detection:** counts per-file edits and prompts a rethink after N edits.
- **Reasoning budget:** xhigh for planning, high for implementation, xhigh for verification scored 66.5%; xhigh throughout scored 53.9% due to timeouts.
- **Trace analysis:** a LangSmith-trace skill drives the edits; the authors warn about task-specific overfitting.
