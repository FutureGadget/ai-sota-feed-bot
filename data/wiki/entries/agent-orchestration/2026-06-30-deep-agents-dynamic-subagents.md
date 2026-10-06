---
title: "Deep Agents dynamic subagents drive fan-out from code, not one tool call per worker"
date: 2026-06-30
theme: code-driven
evidence: [f27164f724f79fa3]
also: [multi-agent]
---
LangChain's **dynamic subagents** in Deep Agents orchestrate sub-agents from a program instead of having the model emit one tool call per worker. Coverage is **guaranteed by control flow**: every item in a fan-out gets a worker because the code says so, not because the model remembered to call one.

The coordination layer becomes ordinary, deterministic, testable code wrapped around non-deterministic agents.
