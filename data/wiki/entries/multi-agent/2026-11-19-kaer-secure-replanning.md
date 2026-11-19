---
title: "Kaer shields orchestrator replanning from malicious agent feedback with templates and repair operators"
date: 2026-11-19
theme: oversight-and-safety
evidence: [dfde2d652caf6073]
also: [prompt-injection, agent-planning]
---
Orchestrator-style systems revise plans from sub-agent feedback, so a malicious agent can embed instructions in that feedback and hijack the replan. Per-tool access control and pre-execution policy do not cover this phase.

Kaer passes diagnostics to the planner only through **abstract failure templates**, restricts revisions to a set of **deterministic repair operators**, and checks every modified plan against preset policies. On its Cintra benchmark of replanning attacks, Kaer was more robust than undefended Magentic-One and the ControlValve defense, with utility comparable to ControlValve; templates cost some utility on select tasks. For builders: sub-agent output is untrusted input to the planner, and replanning needs the same quarantine as tool output.
