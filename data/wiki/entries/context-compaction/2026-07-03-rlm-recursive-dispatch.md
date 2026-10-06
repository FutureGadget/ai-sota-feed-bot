---
title: "Recursive language models in Deep Agents fan out over context chunks instead of compacting"
date: 2026-07-03
theme: skipping-compaction
evidence: [8688a4c832b1b52a]
also: [agent-memory]
---
LangChain's Deep Agents implements the **recursive language model (RLM)** pattern: the agent writes code that dispatches sub-agents over chunks of context, using dynamic sub-agents and a lightweight code interpreter for grep-, map-, and reduce-style fan-out. On the OOLONG long-context reasoning task, LangChain reports it holds up where turn-by-turn agents break down.

It trades one long-context call for many short ones. That sidesteps context rot rather than compressing around it.
