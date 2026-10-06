---
title: "Deep Agents context modes let a subagent fork the supervisor's context or start isolated"
date: 2026-09-10
theme: shared-context
evidence: [b3d2576e2dbda990]
also: [agent-orchestration]
---
LangChain's Deep Agents adds **context modes**: a supervisor can **fork** its own context into a subagent, which inherits everything seen so far, or start it **isolated**, with a clean context told only what the task needs.

"What does the next agent need to see" becomes a per-handoff switch. Isolated starts are faster, cheaper, and more focused; forking is for subagents that genuinely need the supervisor's history.
