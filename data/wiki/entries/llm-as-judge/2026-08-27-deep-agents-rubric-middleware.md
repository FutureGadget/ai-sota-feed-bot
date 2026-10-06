---
title: "Deep Agents RubricMiddleware puts the grader inside the agent loop"
date: 2026-08-27
theme: structured-verdicts
evidence: [92884e6fce9aba7c]
---
LangChain's Deep Agents **RubricMiddleware** takes a newline-delimited checklist at invocation time and hands it to a separate grader sub-agent. The grader can call tools, such as a test runner, to gather evidence before it rules.

When a criterion fails, the grader's per-criterion feedback is injected back into the conversation and the agent re-runs, up to a configured cap. The rubric becomes a runtime input the agent iterates against, not an offline scoring pass.
