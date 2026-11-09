---
title: "MemoryDojo: every tested memory architecture propagates poisoned instructions across sessions"
date: 2026-11-09
theme: memory-integrity
evidence: [138e084674254809]
also: [prompt-injection]
---
MemoryDojo is a benchmark of 155 multi-session, long-horizon trajectories across four domains that traces a poisoned instruction from the session where it is stored to the later session where it is retrieved and acted on. Across the five memory systems tested, the paper reports that all are susceptible, with large differences in downstream effect depending on how each system processes and retrieves memory. The authors also propose a memory-aware poison optimization that raises attack efficacy and exposes those architectural differences. Paper-reported.

For builders: treat memory writes as an injection path. Choosing a memory architecture is partly a security decision, so test it with a cross-session poisoning trace before relying on it.
