---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: architectures
    title: Tiered and lifecycle memory architectures
    summary: Working, episodic, and long-term tiers are settled practice, now shipped as products on existing infrastructure, with newer work treating memory as a lifecycle of writing, scoping, consolidating, and forgetting.
  - key: local-first-stores
    title: "Build vs. buy: managed services and developer-owned stores"
    summary: Managed memory services compete with a crowded wave of local-first, single-file stores that often retrieve with BM25 plus vectors and no LLM in the loop.
  - key: shared-memory
    title: Sharing memory across agents, isolating it between users
    summary: One memory now serves many agents and tools, which raises write-conflict and organization questions and forces per-user scoping so context doesn't leak between callers.
  - key: recall-and-curation
    title: What to write, when to revoke, how to recall
    summary: Similarity recall misses logically relevant and stale-but-superseded facts, so the work is shifting to revocation, write-time curation, and recall that reasons over the store.
  - key: memory-integrity
    title: Poisoned, hidden, and sycophantic memory
    summary: Persistent memory is a persistent attack surface; poisoned facts, concealed injections, forged reasoning, and sycophancy all pass through the write path.
  - key: measuring-memory
    title: Benchmarks and leaderboards for memory
    summary: Memory evaluation is moving from factual recall to utilization, failure modes, and task completion, scored through fixed pipelines with cost on the axis.
---

## TL;DR
An agent's working memory is its context window, which is finite and resets
between runs. On long-horizon tasks it forgets earlier steps, repeats work, and
loses the user's intent — so "agent memory" (what to persist, where, and how to
recall it) becomes a first-class architecture problem rather than a prompt tweak.

## State of the art
The field has converged on **memory as a tiered system**: the live context
window, an episodic log of past interactions, and a durable store of facts,
preferences, and procedures. That split now ships as real components, often
on infrastructure teams already run (Elasticsearch, Postgres, Redis) and often
exposed over [MCP](/topic/mcp). Newer framing treats memory as a lifecycle:
deciding what to write, scoping it, consolidating, and forgetting.

**The hard questions moved to the write and recall paths.** Similarity search
misses facts that are logically relevant but worded differently, and
append-only stores keep stale facts alive; one study found a memory without
revocation scores below no memory at all. Instruction files like `CLAUDE.md`
show the write-side version: they grow because deleting a rule is riskier than
adding one.

**Build vs. buy is splitting the market.** Managed services sit beside a
crowded wave of local-first, single-file stores. Several of the latter
retrieve with BM25 plus vectors and no LLM in the loop, and report recall in
the mid-90s on LongMemEval.

**Integrity is the open problem.** Memory admits poisoned facts, hidden
injections, forged reasoning, and sycophantic recall, and benchmarks show
that strong recall does not predict whether an agent uses memory well.
Evaluation is maturing toward fixed Add/Search pipelines and cost-aware
scoring.

The counterweight is brute force: 1M-token windows and recursive dispatch let
some runs skip memory engineering (see
[context compaction](/topic/context-compaction)). They don't carry anything
across sessions.

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, revocation, per-user isolation, and recall evaluation — not
a one-time integration. The write path is also a security boundary: anything
an agent stores becomes trusted context later.
