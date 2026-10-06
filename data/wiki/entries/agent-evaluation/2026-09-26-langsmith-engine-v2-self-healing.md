---
title: "LangSmith Engine v2 mines traces for issues, confirms them, and tests candidate fixes"
date: 2026-09-26
theme: eval-in-production
evidence: [e16684fdeb069794]
---
LangSmith **Engine v2** mines production traces and repos to hypothesize issues that have not surfaced yet, tests them, and surfaces confirmed failures. For managed deployments it re-runs offending inputs to confirm, tests candidate fixes against a broader eval set, and opens a PR on request.

It widens eval signals past errors to performance trends (error rate, latency, cost) and inefficient trajectories such as repetitive tool calls. The diagnose-fix-validate loop becomes automated, with a human still approving the change.
