---
title: "Offline monitoring evaluates internal agents from logged activity after the fact"
date: 2026-06-30
theme: monitoring-limits
evidence: [345d694a3d9a314f]
---
"Evaluating Offline Monitoring of Internal AI Agents" studies **monitoring agents from logged activity after the run**, rather than with live instrumentation.

This matters when runtime tracing is incomplete or the agent runs where you can't watch it. The open question is how good such monitors are, which is itself an evaluation problem.
