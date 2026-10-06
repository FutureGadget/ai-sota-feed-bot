---
title: "Claude Code Dynamic Workflows generate a custom execution harness per task"
date: 2026-06-19
theme: code-driven
evidence: [e7f12e82187d72de]
also: [multi-agent]
---
Anthropic described the orchestration behind Claude Code's **Dynamic Workflows**: instead of committing to one fixed shape, the system **generates a custom execution harness for each task** to coordinate a team of sub-agents.

Control flow becomes something the model writes for the job at hand. It adapts per task, but a generated harness is harder to predict and test than a fixed graph, so you need the run traced to debug it.
