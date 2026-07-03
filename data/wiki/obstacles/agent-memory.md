---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: [deep-research]
evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44, 23f07233dca1a9dc, 9283a6f418d96ab7, f42a28fa00ccf0ea, 495bc8d2b48db179, 8688a4c832b1b52a]
updated: 2026-07-02
covers_evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44, 23f07233dca1a9dc, 9283a6f418d96ab7, f42a28fa00ccf0ea, 495bc8d2b48db179, 8688a4c832b1b52a]
---

## TL;DR
An agent's working memory is its context window, which is finite and resets
between runs. On long-horizon tasks it forgets earlier steps, repeats work, and
loses the user's intent — so "agent memory" (what to persist, where, and how to
recall it) becomes a first-class architecture problem rather than a prompt tweak.

## State of the art
The field has converged on **memory as a tiered system** rather than a single
store: short-term/working memory (the live context window), episodic memory
(a log of past interactions), and long-term/semantic memory (durable facts
and preferences). LinkedIn's cognitive-memory writeup frames this split
explicitly and is a useful reference architecture.

The tiered model now has an open, **production-grade instance**: Elastic's
Atlas implements three memory categories on top of Elasticsearch (infra many
teams already run), exposes them to agents over [MCP](/topic/mcp), keeps
per-user memory isolated, and reports evaluation numbers rather than a demo —
pushing "cognitive memory" from reference diagram to shippable component.
Practitioners read this as memory *leaving the "remember this" demo phase*
and becoming a real engineering layer.

The hard questions are no longer "should the agent have memory" but **what
to write, when to write it, and how to recall the right slice cheaply** —
which is where the two linked solutions diverge: retrieval from an external
store (vector/graph knowledge bases) versus keeping the working set small via
compaction.

Recall itself is getting scrutinized: "Root Memories" shows similarity-based
retrieval misses memories that are *logically* relevant rather than
lexically close to the query, so the recall step has to reason over what's
stored, not just embed-and-rank (see
[vector/graph retrieval](/topic/vector-kb)).

A related, more mechanical structural lever is shipping in production
too: AWS AgentCore Memory adds structured metadata filtering across
configuration, ingestion, and retrieval, so a query narrows by
business-dimension fields (department, priority, ticket type, and similar)
before similarity ranking ever runs, with separate namespace-based
isolation for per-user/per-session/per-tenant boundaries. That's exact-field
pre-filtering, not the logical reasoning over lexically-distant memories
Root Memories argues for — but it's the same underlying shift, structure
narrowing what similarity search has to search over, now as a shipped
enterprise feature rather than a research argument.

The market is splitting along a **build-vs-buy** seam: managed offerings
(e.g. Cloudflare's persistent Agent Memory service) move memory toward
buy-able infrastructure, while a parallel wave of local-first, single-file,
developer-owned stores treats memory as a component you install and own
rather than a service you rent:

- bi-temporal memory in one SQLite file (Memharness)
- local-first encrypted memory over MCP (Cortex)
- curated file-based project memory (Brain2.0)
- graph-based associative memory built with ~zero LLM calls (FERNme)
- layered project/session/docs memory purpose-built for coding agents (Knotic)

As that wave matures the question shifts from "where does memory live" to
**"how does it follow the agent"**: a durable, S3-backed filesystem that
mounts the same memory markdowns across a laptop and the cloud treats the
store as a *portable substrate* you sync between runtimes rather than a
per-platform silo — the build-it-yourself answer to the cross-platform
consistency that managed services sell.

The same portability instinct now extends to **sharing memory across
agents, not just across runtimes**: Sibyl is a self-hosted, multi-user
memory system (built on SurrealDB) that many parallel coding agents on the
same machine or team read and write through a CLI or MCP, reporting 96.96%
strict recall@5 on LongMemEval-S with no LLM in the retrieval path —
evidence that a shared, developer-owned memory substrate can both scale to
many concurrent agents and stay cheap to query.

A recurring design theme in this wave is **richer temporal modeling**:
bi-temporal stores track both when a fact was true and when the agent
learned it, so recall can reason about staleness instead of returning
whatever embeds nearest.

A second, cost-driven theme is **cheap, mechanical writes**: rather than
calling an LLM to decide what to store, newer stores build the memory
structure deterministically — FERNme forms associative memory tags from
fuzzy edges and a Hebbian co-occurrence rule, and local-first stores like PMB
index writes with a hybrid BM25-plus-vector retriever in a single SQLite
file — so persisting and recalling what an agent learns stops being a
per-turn token bill.

A third, newer theme is **memory integrity**: persistent memory is also a
persistent attack surface. A reproducible benchmark shows agent-memory
systems readily admit *poisoned facts* — adversarial or wrong entries that
get written once and then retrieved as trusted context on every later turn —
which makes write-time validation and provenance, not just recall quality,
part of the memory-engineering job (and ties memory to
[prompt injection](/topic/prompt-injection)).

Integrity is one slice of a broader move to **make memory quality
measurable**: a dedicated benchmark for the *failure modes* of agent memory
— not just poisoning but forgetting, stale recall, and retrieval that
returns the wrong slice — turns "did the memory layer help" into a number
you can regress on, the same trajectory evaluation took
([agent benchmarks](/topic/agent-benchmarks)). That failure surface now has
a fourth axis: MemSyco-Bench shows retrieved memories can push an agent
toward **sycophancy**, biasing it to agree with a stored preference instead
of giving the correct answer — a failure in how memory shapes the response,
not just what gets recalled.

Underneath the architecture debate the practitioner consensus is also
consolidating: vendor guides now lay out the same tiered split (short-term
context plus durable long-term store) as settled practice and add a feedback
loop on top — analyze the agent's own *traces* to decide what is worth
remembering and to let it improve across runs — so memory is increasingly
framed as something the agent curates from its own history, not just a
place facts are dumped.

## What's new
Structured, filterable retrieval lands as a **shipped enterprise feature**:
AWS AgentCore Memory exposes metadata filters across ingestion and
retrieval so a query narrows by business-dimension fields before similarity
ever runs — a more mechanical, production-ready cousin of this week's
structured-retrieval research (see [vector/graph retrieval](/topic/vector-kb)).
Memory-quality benchmarking
gains a fourth failure axis — MemSyco-Bench shows retrieved memories can
induce sycophancy, not just wrong or stale recall — and Deep Agents'
recursive-language-model pattern offers an alternative to flat
summarization: dispatch subagents over context chunks instead of compacting
the whole window (see [context compaction](/topic/context-compaction)). The
local-first tool wave gains another coding-agent-specific entrant, Knotic's
layered project/session/docs memory.

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, and recall evaluation — not a one-time integration.
