---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: [deep-research]
evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d]
updated: 2026-06-18
covers_evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d]
---

## TL;DR
An agent's working memory is its context window, which is finite and resets
between runs. On long-horizon tasks it forgets earlier steps, repeats work, and
loses the user's intent — so "agent memory" (what to persist, where, and how to
recall it) becomes a first-class architecture problem rather than a prompt tweak.

## State of the art
The field has converged on **memory as a tiered system** rather than a single
store: short-term/working memory (the live context window), episodic memory (a
log of past interactions), and long-term/semantic memory (durable facts and
preferences). LinkedIn's cognitive-memory writeup frames this split explicitly
and is a useful reference architecture. The hard questions are no longer "should
the agent have memory" but **what to write, when to write it, and how to recall
the right slice cheaply** — which is where the two linked solutions diverge:
retrieval from an external store (vector/graph knowledge bases) versus keeping
the working set small via compaction. Managed offerings (e.g. Cloudflare's
persistent Agent Memory service) signal that this is moving from bespoke code to
buy-able infrastructure, which sharpens a build-vs-buy decision for teams.

## What's new
Recent sources push two directions at once: managed persistent-memory services
(Cloudflare) lowering the ops bar, and a survey of open agent-memory stacks
(Letta, Mem0, Graphiti, Cognee) showing the DIY ecosystem maturing around
graph- and vector-backed designs.

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, and recall evaluation — not a one-time integration.
