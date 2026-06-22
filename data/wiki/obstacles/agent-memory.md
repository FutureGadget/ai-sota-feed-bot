---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: [deep-research]
evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8]
updated: 2026-06-22
covers_evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8]
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
the working set small via compaction. The market is splitting along a build-vs-buy
seam: managed offerings (e.g. Cloudflare's persistent Agent Memory service) move
memory toward buy-able infrastructure, while a parallel wave of **local-first,
single-file, developer-owned stores** — bi-temporal memory in one SQLite file
(Memharness), local-first encrypted memory over MCP (Cortex), curated
file-based project memory (Brain2.0), graph-based associative memory built with
~zero LLM calls (FERNme) — treats memory as a component you install
and own rather than a service you rent. A recurring design theme in this wave is
**richer temporal modeling**: bi-temporal stores track both when a fact was true
and when the agent learned it, so recall can reason about staleness instead of
returning whatever embeds nearest. A second, cost-driven theme is **cheap,
mechanical writes**: rather than calling an LLM to decide what to store, newer
stores build the memory structure deterministically — FERNme forms associative
memory tags from fuzzy edges and a Hebbian co-occurrence rule — so persisting
what an agent learns stops being a per-turn token bill.

## What's new
The local-first wave is now also attacking the **write cost** of memory: FERNme
builds an associative memory graph from fuzzy edges and a Hebbian co-occurrence
rule that updates with ~zero LLM calls, so persisting what an agent learns stops
being a per-turn token bill — joining bi-temporal SQLite stores (Memharness) and
encrypted local memory over MCP (Cortex) in treating memory as an installable,
developer-owned component rather than a metered service.

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, and recall evaluation — not a one-time integration.
