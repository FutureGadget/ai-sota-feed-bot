---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: [deep-research]
evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44]
updated: 2026-06-30
covers_evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44]
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
and is a useful reference architecture — and the tiered model now has an open,
production-grade instance: Elastic's Atlas implements three memory categories on
top of Elasticsearch (infra many teams already run), exposes them to agents over
[MCP](/topic/mcp), keeps per-user memory isolated, and reports evaluation numbers
rather than a demo, pushing "cognitive memory" from reference diagram to shippable
component. Practitioners read this as memory *leaving the "remember this" demo
phase* and becoming a real engineering layer. The hard questions are no longer "should
the agent have memory" but **what to write, when to write it, and how to recall
the right slice cheaply** — which is where the two linked solutions diverge:
retrieval from an external store (vector/graph knowledge bases) versus keeping
the working set small via compaction. Recall itself is getting scrutinized:
"Root Memories" shows similarity-based retrieval misses memories that are
*logically* relevant rather than lexically close to the query, so the recall step
has to reason over what's stored, not just embed-and-rank
(see [vector/graph retrieval](/topic/vector-kb)). The market is splitting along a build-vs-buy
seam: managed offerings (e.g. Cloudflare's persistent Agent Memory service) move
memory toward buy-able infrastructure, while a parallel wave of **local-first,
single-file, developer-owned stores** — bi-temporal memory in one SQLite file
(Memharness), local-first encrypted memory over MCP (Cortex), curated
file-based project memory (Brain2.0), graph-based associative memory built with
~zero LLM calls (FERNme) — treats memory as a component you install
and own rather than a service you rent. As that wave matures the question shifts
from "where does memory live" to **"how does it follow the agent"**: a durable,
S3-backed filesystem that mounts the same memory markdowns across a laptop and
the cloud treats the store as a *portable substrate* you sync between runtimes
rather than a per-platform silo — the build-it-yourself answer to the
cross-platform consistency that managed services sell. A recurring design theme in this wave is
**richer temporal modeling**: bi-temporal stores track both when a fact was true
and when the agent learned it, so recall can reason about staleness instead of
returning whatever embeds nearest. A second, cost-driven theme is **cheap,
mechanical writes**: rather than calling an LLM to decide what to store, newer
stores build the memory structure deterministically — FERNme forms associative
memory tags from fuzzy edges and a Hebbian co-occurrence rule, and local-first
stores like PMB index writes with a hybrid BM25-plus-vector retriever in a single
SQLite file — so persisting and recalling what an agent learns stops being a
per-turn token bill. A third, newer theme is **memory integrity**: persistent
memory is also a persistent attack surface. A reproducible benchmark shows
agent-memory systems readily admit *poisoned facts* — adversarial or wrong
entries that get written once and then retrieved as trusted context on every
later turn — which makes write-time validation and provenance, not just recall
quality, part of the memory-engineering job (and ties memory to
[prompt injection](/topic/prompt-injection)). Integrity is one slice of a
broader move to **make memory quality measurable**: a dedicated benchmark for the
*failure modes* of agent memory — not just poisoning but forgetting, stale
recall, and retrieval that returns the wrong slice — turns "did the memory layer
help" into a number you can regress on, the same trajectory evaluation took
([agent benchmarks](/topic/agent-benchmarks)). Underneath the architecture debate
the practitioner consensus is also consolidating: vendor guides now lay out the
same tiered split (short-term context plus durable long-term store) as settled
practice and add a feedback loop on top — analyze the agent's own *traces* to
decide what is worth remembering and to let it improve across runs — so memory is
increasingly framed as something the agent curates from its own history, not just
a place facts are dumped.

## What's new
The tiered "cognitive memory" model just got a **major-vendor open
implementation**: Elastic's Atlas puts short/episodic/long-term memory on
Elasticsearch, serves it to agents over [MCP](/topic/mcp), isolates it per user,
and ships with evaluation numbers — the clearest sign yet that memory is, in
practitioners' words, *leaving the "remember this" demo phase* and becoming a
production layer built on infra teams already operate (the same "ride an existing
substrate" instinct shows up at the quirky end too, with agents that repurpose an
email outbox as their memory store). That lands on top of memory quality getting
**benchmarked, not just architected** (a suite for the full failure surface —
forgetting, stale/wrong recall, poisoned entries), memory as a **portable
substrate** (an S3-backed filesystem mounting the same markdowns across laptop and
cloud), **trace-driven curation**, and the established concerns of **integrity**
and the local-first wave (FERNme, PMB, Memharness, Cortex).

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, and recall evaluation — not a one-time integration.
