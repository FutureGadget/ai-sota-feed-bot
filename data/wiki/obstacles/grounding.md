---
slug: grounding
kind: obstacle
title: "An agent's answer is only as good as what it retrieved — and whether it can prove it"
area: grounding
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1]
updated: 2026-07-16
covers_evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1]
---

## TL;DR
A fluent agent answer isn't the same as a grounded one: the model will answer
past what it actually retrieved unless the retrieval was current, the right
slice, and cheap enough to fetch — and unless something checks that the
answer is actually backed by what came back. Grounding is the retrieval and
attribution problem underneath [agent memory](/topic/agent-memory); this
page tracks it as its own obstacle because retrieval quality and provenance
fail in ways a memory-tiering decision doesn't touch.

## State of the art
The retrieval stack is consolidating into single, self-hosted **gateways**
rather than staying bespoke per project: Orbit packages file RAG, vector RAG
across five-plus backends (Chroma, Qdrant, Pinecone, Weaviate, pgvector,
FAISS), and natural-language-to-query translation over SQL, NoSQL, and REST
sources into one open toolkit — treating "which store, which query language"
as a routing decision inside the gateway rather than a separate integration
per source.

**Deterministic retrieval is a live alternative to embedding everything**:
a production Postgres pattern assembles context by writing a plain SQL query
("how would a human solve this?") instead of reaching for similarity search
by default, reserving HNSW-indexed vector search — with quantization for
roughly 4x faster lookups — for the genuinely fuzzy slice of the problem.
It's the structured-recall argument [agent memory](/topic/agent-memory)
already makes, applied to what an agent fetches rather than what it
remembers.

**Fetching itself is a grounding cost, not just a token-cost line item**: a
raw Wikipedia page runs roughly 68,240 tokens versus 3,000-5,000 once
converted to markdown by a stealth-browser fetch tool — the same
information, with most of the difference being boilerplate the model has to
read before it can ground on the part that matters (see
[agent cost](/topic/agent-cost) for the token-price side of the same fact).

**Attribution is now a measured axis**, not a vibe: ResearchQA scores
whether an LLM's answer over scientific papers is actually backed by
verifiable citations rather than just scoring the answer text, and a
tool-adaptive reranker conditions its reranking on which retrieval tool
produced each candidate — both targeting the specific failure mode where a
model answers fluently past what its retrieved context actually supports.

**The retriever itself keeps improving**, which moves the ceiling on every
technique above it: NVIDIA's Nemotron 3 Embed line ranks #1 overall on RTEB
(a multilingual, domain-spanning retrieval benchmark) at 78.5%, with its
smaller 1B variant cutting the error rate of its own predecessor by 27% —
concretely, better retrieval means an agent finds the relevant evidence
sooner and burns fewer reasoning turns and search calls getting there, so
retrieval quality is also a cost and latency lever, not just an accuracy one
(cross-ref [agent cost](/topic/agent-cost), [agent latency](/topic/agent-latency)).
**Structure is also arriving in a place agents specifically ground on —
codebase documentation**: OpenWiki 0.2 adopts OKF, a proposed open standard
that puts YAML front matter (tags, categories, timestamps) and directory
index files onto wiki pages, so an agent can filter to "every doc tagged
`billing`" directly instead of running an open-ended search — the same
structured-recall argument this page already makes for SQL over embeddings,
applied to the docs an agent grounds coding answers on.

## What's new
The retriever itself got measurably better: NVIDIA's Nemotron 3 Embed ranks
#1 on RTEB, and its smaller variant cuts its predecessor's error rate by
27% — moving the ceiling on every downstream grounding technique, since a
stronger retriever means fewer wasted reasoning turns before the agent finds
what it needed. Separately, OpenWiki 0.2 puts structured metadata (tags,
categories) directly onto codebase-documentation pages via the OKF format,
letting an agent filter to a category or tag instead of running an
open-ended search — structured recall applied to the docs agents ground
coding answers on.

## Why it matters for platform engineers
Grounding is the trust layer underneath every agent answer that cites a
source or claims a fact: get it wrong and the agent is fluent but
unverifiable, which is worse than an obvious failure because users don't
know to distrust it. The engineering job splits three ways — pick the
retrieval architecture (vector, graph, SQL, or a gateway spanning all
three), budget the token cost of fetching before it enters context (cross-ref
[cost](/topic/agent-cost)), and measure attribution directly rather than
assuming a fluent answer is a grounded one.
