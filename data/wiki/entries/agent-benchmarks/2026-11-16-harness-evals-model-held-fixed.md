---
title: "Evaluate harness changes like model changes: hold the model fixed and run paired, repeated trials"
date: 2026-11-16
theme: own-workload
evidence: [0a29263254186c1e]
also: [agent-orchestration]
---
`harness-evals`, a small Python library, inverts the usual benchmark: the **model, endpoint, settings, tasks, and checks stay fixed**, and only the harness or workflow changes.

You write use-case tasks with hard checks and a short adapter per harness. It reports repeated-run success, reliability, cost, latency, and model usage with intervals, plots designs on two metrics at once, marks the Pareto-optimal ones, and returns **adopt, reject, or keep investigating**. Its demo compares five designs of one support assistant, from a plain agent to a workflow with no agent (simulated model, so the numbers describe the simulation only).

For builders: prompt, tool, and topology changes deserve the same paired evaluation as model swaps, and "no agent" belongs on the comparison.
