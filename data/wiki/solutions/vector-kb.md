---
slug: vector-kb
kind: solution
title: "External knowledge base: vector and graph retrieval"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8, eb5267262e7d31c8, 0657f60e37a5d3d2, 4532a97181f06d93, ca2de3ecb9f0eb55, 9a34e69e3da208ca, 648e4fc20120543d, 567c0f7008740f1a, c54c0758c14bd2c6, 04ca1a84bd09d4e2, 9283a6f418d96ab7, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f]
updated: 2026-07-16
covers_evidence: [425a66a9c84b30ae, 5c5003b8c444211d, 2d698f04404f697d, e596543fdecfca96, 623de2bad771dca8, eb5267262e7d31c8, 0657f60e37a5d3d2, 4532a97181f06d93, ca2de3ecb9f0eb55, 9a34e69e3da208ca, 648e4fc20120543d, 567c0f7008740f1a, c54c0758c14bd2c6, 04ca1a84bd09d4e2, 9283a6f418d96ab7, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f]
---

## TL;DR
Push long-term memory *out* of the context window into an external store —
embeddings in a vector index, and/or a knowledge graph of entities and
relations — and retrieve only the relevant slice at each step. This is how an
agent "remembers" more than fits in a prompt.

## State of the art
Pure top-k vector similarity is increasingly treated as a floor, not the
answer: practitioners report that **hybrid retrieval** (dense vectors +
lexical/keyword + metadata filters, often with a rerank pass) is needed for
production recall, and that **knowledge graphs** capture connected facts
that flat embeddings miss. The open ecosystem (Letta, Mem0, Graphiti,
Cognee) packages these as agent-memory layers with different stances on
graph vs. vector vs. hybrid.

A parallel move puts that layer on a **commodity datastore you already
run**: BetterDB ships an open (MIT) Valkey-native context layer that folds
agent memory, semantic plus multi-tier caching, and typed retrieval onto a
single Valkey/Redis instance, local or hosted — collapsing the "buy a
separate vector DB" hop into the cache you already operate, and tying memory
and caching into one substrate rather than two systems to keep consistent.

The same "ride infrastructure you already run" move is now coming from
**incumbents**: Elastic's Atlas builds tiered agent memory directly on
Elasticsearch and serves it over [MCP](/topic/mcp), so the retrieval store
is the search cluster the team already operates rather than a new
dependency.

Retrieval quality, meanwhile, is increasingly treated as a
**data-and-embedding** problem, not just an index choice: a production
deployment at Target replaces rule-based campaign matching with embeddings
plus vector search plus an LLM rerank, and permutation-invariant embedding
fine-tuning fixes a concrete failure where field order in serialized
structured records skews similarity — both pointing at recall quality being
earned in how records are embedded and ranked, not in the vector DB brand.

Strong results are achievable **without an LLM in the recall path** (a
local store hitting high LongMemEval recall), underscoring that retrieval
quality is an engineering problem, not a model-scale one.

The **embedding model itself** is also a live lever, not a solved commodity
choice: NVIDIA's Nemotron 3 Embed line ranks #1 overall on RTEB (78.5% on the
flagship 8B model), and its 1B variant cuts its own predecessor's error rate
by 27% — swapping in a stronger embedder moves the ceiling on every retrieval
architecture above without changing the index, chunking, or rerank strategy
at all.

The category is also being challenged from **outside vectors entirely**,
with the shared claim that exact, structured, temporally aware recall often
beats fuzzy similarity — and can be built and updated without per-turn LLM
cost:

- bi-temporal relational stores (Memharness, a single SQLite file) lean on
  time and structure rather than embeddings
- vector-symbolic / algebraic memory (VSA) proposes binding and bundling
  operations *instead of* RAG-style nearest-neighbour lookup
- graph-based associative stores build the structure from co-occurrence
  rather than embeddings (FERNme grows a memory graph with fuzzy edges and a
  Hebbian co-occurrence rule, keeping the LLM out of the *write* path as
  well as the read path)

A complementary critique targets the *query* side: "Root Memories" shows
similarity-based retrieval misses memories that are **logically** rather
than lexically relevant — the fact you need to answer is implied by what's
stored, not embedded near the question — so recall has to reason over
stored memories, not just rank them by distance, or it silently drops the
load-bearing one.

The vector-vs-graph split now has a **cheaper way to get the graph**:
TIGRAG builds its knowledge graph from token co-occurrence statistics (a
sliding-window count over the corpus) instead of an LLM-extraction pipeline,
then combines that graph with neural reranking for multi-hop retrieval —
matching or beating dense and LLM-extracted GraphRAG on multi-hop QA while
cutting indexing time, inference latency, and prompt footprint, which
weakens the standard objection that graph construction is too slow and
expensive to run at production scale.

**Provenance** — the third gap enterprise GraphRAG guidance names alongside
global context and multi-hop reasoning — now has a dedicated measurement
instrument: ResearchQA benchmarks whether an LLM's answer over scientific
papers is actually supported by verifiable citations, rather than scoring
answer text alone, giving the "is this grounded or just fluent" question a
number instead of a spot-check. On the reranking side, a **tool-adaptive**
reranker conditions its reranking on which retrieval tool produced each
candidate rather than treating every hit the same way, aimed at the
factual-hallucination failure mode that shows up when a purely parametric
LLM answers past what its retrieved context actually supports — a further
refinement of the hybrid-retrieval-plus-rerank stack already converged on.

## What's new
The embedding model itself improved: NVIDIA's Nemotron 3 Embed ranks #1
overall on RTEB, and its smaller 1B variant cuts its predecessor's error rate
by 27% — a ceiling-raising change orthogonal to the hybrid-retrieval,
graph, and provenance work below, since it improves every architecture that
sits on top of an embedding.

Provenance gets its own benchmark: ResearchQA scores whether an LLM's answer
over scientific papers is actually backed by verifiable citations, turning
"is this grounded or just fluent" into a measured number. A tool-adaptive
reranker extends the hybrid-retrieval-plus-rerank stack by conditioning the
rerank step on which tool produced each candidate, targeting the
factual-hallucination failure mode of a purely parametric answer.

A practitioner framing of the same split now has a name for why plain
vector RAG plateaus: enterprise GraphRAG guidance argues traditional vector
retrieval falls short on **global context, multi-hop reasoning, and
provenance** specifically, and that the fix is pushing structure down into
the data layer rather than adding more orchestration logic on top —
reinforcing that the graph-vs-vector choice is about what vector similarity
structurally cannot answer, not implementation taste.

The critique of pure similarity also hits the **query side**: "Root
Memories" benchmarks show semantic-similarity retrieval misses *logically*
critical memories (relevant by implication, not embedding distance), arguing
recall must reason over stored facts rather than rank them by
nearest-neighbor.

That sharpens the live "is a vector DB even the right primitive" question
already raised by non-vector designs — all arguing structured, exact recall
can beat embedding similarity:

- bi-temporal SQLite (Memharness)
- algebraic/vector-symbolic memory as an explicit RAG alternative (VSA)
- Hebbian co-occurrence graphs (FERNme)

A quieter trend runs the other way on **infrastructure**: rather than a new
store, BetterDB puts memory + semantic/multi-tier caching + typed retrieval
on a commodity Valkey/Redis instance you already operate, and Elastic's
Atlas builds tiered memory on Elasticsearch served over MCP — both letting
the memory layer ride existing ops instead of adding a dedicated vector
database. That list now includes a general-purpose database vendor directly:
AlloyDB ships vector/hybrid search and natural-language querying as AI
functions on the database itself. AWS's AgentCore Memory pushes the same
"ride what you have" instinct into query shaping — structured metadata
filtering across ingestion/config/retrieval for multi-tenant enterprise use.

And a pair of **production/data signals** (Target's embeddings-plus-rerank
campaign matcher, permutation-invariant embedding tuning for structured
records) reinforce that recall quality is won in embedding and ranking
choices, not in the store itself.

The "ride infrastructure you already run" pattern now reaches **general-purpose
databases**: Google's AlloyDB ships AI functions with vector and hybrid search
plus natural-language querying built into the database itself, alongside
Elastic (Atlas on Elasticsearch) and BetterDB (Valkey/Redis) — a growing set of
incumbents making the operational datastore double as the retrieval layer
instead of adding a dedicated vector DB. On the query-shaping side, AWS's
AgentCore Memory adds **structured metadata filtering** across ingestion,
config, and retrieval, letting enterprise multi-tenant deployments narrow
recall by metadata (tenant, doc type, time range) rather than similarity
alone — a practical complement to the hybrid dense-plus-lexical retrieval
already converged on.

## Trade-offs
Adds a retrieval hop (latency) and an index to keep fresh and consistent;
recall quality is only as good as chunking, embeddings, and reranking, and
is hard to evaluate. Graphs add modeling and maintenance cost but answer
multi-hop/connected queries vectors can't.

Best when the durable knowledge is large, queried sparsely, and changes
slower than every turn.

## Why it matters for platform engineers
This is the "buy a database for your agent's brain" path: it scales memory well
beyond the context window and is independently testable, but it turns memory into
a retrieval system you own — with its own freshness, eviction, and eval burden.
Pairs with, rather than replaces, [context compaction](/topic/context-compaction).
