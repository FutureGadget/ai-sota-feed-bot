---
slug: vector-kb
kind: solution
title: "External knowledge base: vector and graph retrieval"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: hybrid-and-graph
    title: "Beyond top-k vectors: hybrid retrieval and knowledge graphs"
    summary: Production recall needs dense plus lexical retrieval with a rerank, and graphs for multi-hop and provenance; graph construction is getting cheaper without LLM extraction.
  - key: datastores-you-run
    title: Retrieval on the datastore you already operate
    summary: Valkey, Elasticsearch, AlloyDB, and DynamoDB now double as the vector layer, with metadata filters for tenancy, removing the separate vector DB and its sync job.
  - key: recall-quality
    title: Recall is won in embeddings and ranking, not the store
    summary: Embedder choice, record serialization, and reranking move recall more than the index brand, and strong recall is reachable with no LLM in the path.
  - key: beyond-vectors
    title: Structured and non-vector memory designs
    summary: Bi-temporal SQL, vector-symbolic algebra, and co-occurrence graphs argue exact, structured recall can beat similarity for agent memory; most are early projects.
---

## TL;DR
Push long-term memory *out* of the context window into an external store —
embeddings in a vector index, and/or a knowledge graph of entities and
relations — and retrieve only the relevant slice at each step. This is how an
agent "remembers" more than fits in a prompt.

## State of the art
**Top-k vector similarity is the floor, not the answer.** Production stacks
converge on hybrid retrieval: dense vectors plus BM25-style lexical search,
fused (for example with Reciprocal Rank Fusion), filtered by metadata, then
reranked. Knowledge graphs cover what flat embeddings structurally miss:
global context, multi-hop questions, and provenance. Graph construction is
also getting cheaper, with co-occurrence graphs replacing LLM extraction.

**The store is consolidating into infrastructure teams already run.** Valkey,
Elasticsearch, AlloyDB, and DynamoDB all now serve vector search next to the
operational data, so a separate vector database and its sync job are
increasingly optional. The trade is vendor-specific billing and features
rather than a new system to operate.

**Recall quality is earned upstream of the index.** The embedding model, how
structured records are serialized before embedding, and the rerank step move
results more than the choice of store. A local store can reach high
LongMemEval recall with no LLM in the path.

**The open question is whether similarity is the right primitive at all.**
Bi-temporal relational stores, vector-symbolic memory, and co-occurrence
graphs argue for exact, structured, time-aware recall. Benchmarks such as
Root Memories show similarity search misses facts that are logically, not
lexically, relevant. Most of these alternatives are still single projects,
so treat them as design pressure on the vector default, not replacements.

## Trade-offs
Adds a retrieval hop (latency) and an index to keep fresh and consistent;
recall quality is only as good as chunking, embeddings, and reranking, and
is hard to evaluate. Graphs add modeling and maintenance cost but answer
multi-hop/connected queries vectors can't.

Folding vectors into an existing datastore removes a sync job but ties
retrieval features and pricing to that vendor.

Best when the durable knowledge is large, queried sparsely, and changes
slower than every turn.

## Why it matters for platform engineers
This is the "buy a database for your agent's brain" path: it scales memory well
beyond the context window and is independently testable, but it turns memory into
a retrieval system you own — with its own freshness, eviction, and eval burden.

Check first whether the database you already run can serve vectors before
adding another. Pairs with, rather than replaces,
[context compaction](/topic/context-compaction); see
[grounding](/topic/grounding) for retrieval quality and attribution.
