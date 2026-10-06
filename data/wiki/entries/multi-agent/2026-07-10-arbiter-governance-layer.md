---
title: "An arbiter agent settles planner-coder disagreements by checking code against the plan"
date: 2026-07-10
theme: oversight-and-safety
evidence: [8e0e2c22560bbc7b]
also: [agent-orchestration]
---
In an InfoQ presentation, Itamar Friedman describes an **arbiter** role that resolves disagreement between a planning agent and a coding agent by **checking the code against the plan**, not trusting either agent's self-report. It only works when the plan is specified in enough detail to verify against.

He packages parallel testing, review, and context-retrieval agents plus the arbiter as a governance layer: **distinct credentials per agent role** and communication over human-readable channels such as GitHub or chat rather than hidden logs.
