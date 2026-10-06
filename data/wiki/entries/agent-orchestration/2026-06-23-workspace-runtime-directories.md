---
title: "Building an orchestration library is mostly workspace, runtime, and directory design"
date: 2026-06-23
theme: runtime-substrate
evidence: [296564a4c4e09d02]
also: [multi-agent]
---
A write-up on designing an agent orchestration library reports that the load-bearing decisions are **where each sub-agent runs, what filesystem and state it sees, and how its outputs are isolated and collected**, not clever agent roles.

Orchestration is as much an execution-environment problem as a control-flow one. Budget for the plumbing.
