---
slug: vector-kb
kind: solution
title: "External knowledge base: vector and graph retrieval"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8]
updated: 2026-06-20
covers_evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8]
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
SQLite file) lean on time and structure rather than embeddings, and
vector-symbolic / algebraic memory (VSA) proposes binding and bundling
operations *instead of* RAG-style nearest-neighbour lookup. The shared claim is
that for an agent's facts-and-preferences memory, exact, structured, temporally
aware recall often beats fuzzy similarity.

## What's new
The "is a vector DB even the right primitive" question is now live: alongside
hybrid retrieval and graphs, non-vector designs — bi-temporal SQLite stores
(Memharness) and algebraic/vector-symbolic memory positioned explicitly as a
RAG alternative (VSA) — argue that structured, exact recall can outperform
embedding similarity for agent memory.

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
