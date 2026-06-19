---
slug: multi-agent
kind: obstacle
title: "Coordinating multiple agents adds more failure than capability"
area: multi-agent
status: active
solutions: [agent-orchestration, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [64ad8e685ed41a9b, 19e4caf222bfb0d9, e7f12e82187d72de, f961ee6418699914]
updated: 2026-06-19
covers_evidence: [64ad8e685ed41a9b, 19e4caf222bfb0d9, e7f12e82187d72de, f961ee6418699914]
---

## TL;DR
Splitting a job across several agents promises specialization and parallelism,
but every handoff is a lossy interface and each added agent multiplies the ways
the system can stall, loop, or disagree. Coordination overhead routinely eats
the gains — the hard part isn't building the agents, it's getting them to work
together without costing more than one good agent would.

## State of the art
The conversation is shifting from "more agents is better" to characterizing
*when* multi-agent actually helps, and the recurring answer is that the
**communication structure dominates the agent count**. DPBench studies the
structural determinants of multi-agent LLM coordination directly — which
topologies and role assignments make collaboration pay off versus add noise.
Cost is the second axis: Stanford's DeLM reports cutting multi-agent task cost
by roughly half by *removing the central orchestrator*, evidence that a single
coordinating agent is both a token bottleneck and a single point of failure.
Orchestration itself is becoming dynamic rather than hand-wired — Anthropic's
writeup on Claude Code's Dynamic Workflows describes generating a custom
execution harness per task to coordinate sub-agents instead of committing to one
fixed shape. Meanwhile practitioners are still hunting for frameworks where
*heterogeneous* models genuinely collaborate (route refactors to one model,
codegen to another), which is really a routing-and-handoff problem, not a model
problem. The durable lesson: who talks to whom, in what format, and under whose
control is the dominant variable.

## What's new
Evidence is converging that *topology*, not the number of agents, drives both
coordination quality and cost — DPBench formalizes the structural determinants,
DeLM shows decentralizing away from a central orchestrator cuts task cost ~50%,
and Anthropic is now generating execution harnesses per task rather than fixing
a single coordination shape.

## Why it matters for platform engineers
Every extra agent is extra tokens, extra latency, and extra failure surface, so
a multi-agent design has to clear a hard bar: beat a single well-prompted agent
on cost *and* reliability — and it often doesn't. The engineering job is
choosing a topology (orchestrator-worker vs. decentralized), writing strict
handoff contracts so one agent's output is safely another's input, and budgeting
the communication overhead up front. Crucially it needs an eval (see
[agent benchmarks](/topic/agent-benchmarks)) that proves the extra agents paid
for themselves, because the default failure mode is paying N× the cost for a
result a single agent could have produced.
