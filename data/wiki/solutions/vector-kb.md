---
slug: vector-kb
kind: solution
title: "External knowledge base: vector and graph retrieval"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8, eb5267262e7d31c8, 0657f60e37a5d3d2]
updated: 2026-06-24
covers_evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8, eb5267262e7d31c8, 0657f60e37a5d3d2]
---

## TL;DR
Push long-term memory *out* of the context window into an external store —
embeddings in a vector index, and/or a knowledge graph of entities and
relations — and retrieve only the relevant slice at each step. This is how an
agent "remembers" more than fits in a prompt.

## State of the art
Pure top-k vector similarity is increasingly treated as a floor, not the answer:
practitioners report that **hybrid retrieval** (dense vectors + lexical/keyword +
metadata filters, often with a rerank pass) is needed for production recall, and
that **knowledge graphs** capture connected facts that flat embeddings miss. The
open ecosystem (Letta, Mem0, Graphiti, Cognee) packages these as agent-memory
layers with different stances on graph vs. vector vs. hybrid. Strong results are
achievable without an LLM in the recall path (a local store hitting high
LongMemEval recall), underscoring that retrieval quality is an engineering
problem, not a model-scale one. The category is also being challenged from
outside vectors entirely: bi-temporal relational stores (Memharness, a single
SQLite file) lean on time and structure rather than embeddings,
vector-symbolic / algebraic memory (VSA) proposes binding and bundling
operations *instead of* RAG-style nearest-neighbour lookup, and graph-based
associative stores build the structure from co-occurrence rather than embeddings
(FERNme grows a memory graph with fuzzy edges and a Hebbian co-occurrence rule,
keeping the LLM out of the *write* path as well as the read path). The shared
claim is that for an agent's facts-and-preferences memory, exact, structured,
temporally aware recall often beats fuzzy similarity — and can be built and
updated without per-turn LLM cost. A complementary critique targets the *query*
side: "Root Memories" shows similarity-based retrieval misses memories that are
**logically** rather than lexically relevant — the fact you need to answer is
implied by what's stored, not embedded near the question — so recall has to reason
over stored memories, not just rank them by distance, or it silently drops the
load-bearing one.

## What's new
The critique of pure similarity now hits the query side too: "Root Memories"
benchmarks shows semantic-similarity retrieval misses *logically* critical
memories (relevant by implication, not embedding distance), arguing recall must
reason over stored facts rather than rank them by nearest-neighbor. That sharpens
the live "is a vector DB even the right primitive" question already raised by
non-vector designs — bi-temporal SQLite (Memharness), algebraic/vector-symbolic
memory as an explicit RAG alternative (VSA), and Hebbian co-occurrence graphs
(FERNme) — all arguing structured, exact recall can beat embedding similarity.

## Trade-offs
Adds a retrieval hop (latency) and an index to keep fresh and consistent; recall
quality is only as good as chunking, embeddings, and reranking, and is hard to
evaluate. Graphs add modeling and maintenance cost but answer multi-hop/connected
queries vectors can't. Best when the durable knowledge is large, queried
sparsely, and changes slower than every turn.

## Why it matters for platform engineers
This is the "buy a database for your agent's brain" path: it scales memory well
beyond the context window and is independently testable, but it turns memory into
a retrieval system you own — with its own freshness, eviction, and eval burden.
Pairs with, rather than replaces, [context compaction](/topic/context-compaction).
