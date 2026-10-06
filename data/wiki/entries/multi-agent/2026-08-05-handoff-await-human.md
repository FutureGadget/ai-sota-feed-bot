---
title: "Handoff makes a human-in-the-loop pause a single await human() call"
date: 2026-08-05
theme: oversight-and-safety
evidence: [3e6b22895e62d801]
---
Handoff packages the human-in-the-loop pause as **`await human()`**: one composable call a coordinating agent can await mid-plan, instead of a bespoke state model or a full governance layer.

Human checkpoints become ordinary code at the granularity of one function call. Before relying on it for long waits, check whether the pause survives a process restart.
