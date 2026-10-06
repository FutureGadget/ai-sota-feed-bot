---
slug: grounding
kind: obstacle
title: "An agent's answer is only as good as what it retrieved — and whether it can prove it"
area: grounding
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: retrieval-architecture
    title: "Picking the retrieval architecture: SQL, graph, gateway, or managed service"
    summary: Teams choose per job between exact SQL, knowledge graphs, self-hosted gateways, and managed search; production wins come from governed data layers more than retrieval tricks.
  - key: better-retrievers
    title: Better retrievers and smarter search effort
    summary: Stronger and multimodal embedders, structured chart extraction, learned per-query search depth, and set-sufficiency recovery each raise recall without changing the store.
  - key: context-budget
    title: Cutting what retrieval puts into context
    summary: Raw fetched pages waste tens of thousands of tokens; pre-compression, reusable compression views, and distraction-resistant models shrink or harden the retrieved context.
  - key: adversarial-evidence
    title: Evidence that misleads without being false
    summary: Truthful but reordered, nearby, or embedding-mimicking evidence redirects agents; defenses normalize presentation or screen documents, and none transfers cleanly yet.
  - key: proving-attribution
    title: Proving the answer is backed by its source
    summary: Attribution is now measured and enforced, with citation benchmarks, per-claim source verifiers for MCP agents, pre-execution checks against ground truth, and rule engines that decide while RAG explains.
---

## TL;DR
A fluent agent answer isn't the same as a grounded one: the model will answer
past what it actually retrieved unless the retrieval was current, the right
slice, and cheap enough to fetch — and unless something checks that the
answer is actually backed by what came back. Grounding is the retrieval and
attribution problem underneath [agent memory](/topic/agent-memory).

## State of the art
**Retrieval architecture is a per-job choice, not a default to embeddings.**
Production teams answer exact questions with plain SQL, use knowledge graphs
for connected and provenance-heavy questions, and reserve vector search for
the fuzzy slice. Gateways, self-hosted or managed, route across stores. The
strongest production results credit a governed data layer underneath the
agent, such as dbt and a semantic model, more than the retrieval method.

**The retriever keeps improving under every architecture.** Better text and
multimodal embedders, structured extraction of charts, learned control of
how much to search per query, and recovering a *sufficient set* of evidence
rather than the top-ranked passages all raise recall without changing the
store. Better retrieval also means fewer search calls, so it is a cost and
latency lever.

**What enters context is a budget.** A raw web page can cost tens of
thousands of tokens of boilerplate. Pre-compression, reusable compression
views, and models hardened against distracting context all attack the same
waste.

**The open problem is evidence that is true but misleading.** Reordered
salience, true evidence for a nearby question, and poisoned embeddings that
mimic benign entries all redirect agents without a single false claim or
injected instruction. Published defenses cut attack success but do not
transfer cleanly across datasets or attack types.

**Attribution is becoming enforceable.** Benchmarks score citation support,
verifiers check per claim that an MCP agent cites the right source, runtime
guards check actions against ground truth before they execute, and
auditable domains split the decision (rules) from the explanation (RAG).

## Why it matters for platform engineers
Grounding is the trust layer underneath every agent answer that cites a
source or claims a fact: get it wrong and the agent is fluent but
unverifiable, which is worse than an obvious failure because users don't
know to distrust it. The engineering job splits three ways — pick the
retrieval architecture (vector, graph, SQL, or a gateway spanning all
three; see [vector-kb](/topic/vector-kb)), budget the token cost of fetching
before it enters context (cross-ref [cost](/topic/agent-cost)), and measure
attribution directly rather than assuming a fluent answer is a grounded one.
