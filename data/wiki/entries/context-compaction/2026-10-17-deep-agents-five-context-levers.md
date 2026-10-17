---
title: "Deep Agents keeps long-running context focused with offloading, summarization, skills, subagents, and memory"
date: 2026-10-17
theme: curating-the-working-set
evidence: [eeb5997da7760442]
---
LangChain's Deep Agents post argues that long-running agents degrade as context piles up, and lays out five levers to keep the window focused: **offloading** large tool output, **summarization**, **skills** loaded on demand, **subagents** with isolated context, and persistent **memory**.

For builders: compaction is one lever among five. Offloading and subagent isolation avoid putting the tokens in context at all, so they carry no summarization loss. See [Agent memory](/topic/agent-memory) for the persistence side.
