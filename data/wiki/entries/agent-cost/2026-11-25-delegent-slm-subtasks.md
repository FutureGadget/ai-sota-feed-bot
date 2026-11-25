---
title: "Delegent keeps the frontier model in charge but hands legwork to a local SLM, cutting cost 59-67%"
date: 2026-11-25
theme: cheaper-models
evidence: [c39c6a595988af5c]
also: [multi-agent]
---
Delegent is a Claude Code harness where the frontier model leads every task but delegates focused subtasks (investigating code, running tests, searching a corpus) to small-model subagents on owned hardware. Unlike a router or cascade, nothing picks a model per task, and nothing is trained. With a **27B FP8** SLM, frontier cost fell **67%** on long-horizon coding and **59%** on agentic search with no task loss; a **2B** laptop model still cut coding cost **66%**. A short instruction reserving main coding for the frontier model produced most of the saving.

For builders: the cheap win is delegating legwork inside one task, not routing whole tasks. Savings scale with how much reading and searching the frontier model was doing.
