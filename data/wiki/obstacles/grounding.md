---
slug: grounding
kind: obstacle
title: "An agent's answer is only as good as what it retrieved — and whether it can prove it"
area: grounding
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1, 20a176e41161c528, 46be0149e39dc713, 5ca9aca0e46db978, 355c8cf2c3a4e36a, 5f80558cf12e2ddc, aec50bce133680e8]
updated: 2026-08-12
covers_evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1, 20a176e41161c528, 46be0149e39dc713, 5ca9aca0e46db978, 355c8cf2c3a4e36a, 5f80558cf12e2ddc, aec50bce133680e8]
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

**A third grounding failure is adversarial, not just noisy**: retrieved
evidence can be entirely true and still redirect a multi-hop agent through
*salience* alone — fact position, emphasis, framing, and semantic proximity,
with no false claims and no embedded instructions. Salience Induction
formalizes this as truth-preserving edits that redirect multi-hop attribute
binding while leaving the retrieval trace looking clean; across five
frontier model families (GPT, Claude, Gemini, DeepSeek, Qwen) and three
agent architectures (ReAct, Reflexion, tool-calling), a 30% edit budget
reaches an 83.3% attack success rate, and the strongest baseline defense
still leaves 75.7% of attacks succeeding. The authors' own input-side
defense, Salience Normalization, cuts that to 15.3% under standard attacks
(23.6% under adaptive ones) — evidence that grounding needs a
retrieval-ordering defense distinct from the content-poisoning and
prompt-injection attacks tracked on [prompt injection](/topic/prompt-injection).

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

**Pre-compression is a fourth retrieval architecture** alongside vector,
graph, and SQL: task-aware knowledge compression (TAKC) pre-compresses an
entire knowledge base into task-specific representations ahead of query
time, targeting the ceiling plain RAG hits on analytical questions that span
hundreds of documents — trading a compression pass up front for a smaller,
denser context at answer time, rather than retrieving and re-reading more
raw pages per query. A parallel finding sharpens *when* to reach for the
agentic version of RAG rather than the naive one: a data-integration study
finds naive RAG keeps facing accuracy and cost limits in enterprise
settings, while an agentic RAG loop — retrieving, checking, and re-querying
rather than fetching once — buys back accuracy at a cost the paper argues is
still worth measuring against the naive baseline before committing to it,
not assuming agentic RAG is automatically the better trade.

**Runtime grounding checks are shipping as a standalone layer**, distinct
from the retrieval architecture itself: ActionRail is an open-source runtime
framework that checks an agent's proposed action or value against
ground-truth business data *before* it executes, rather than only scoring
retrieval quality after the fact — the same value-poisoning failure mode its
benchmark measures (see [agent benchmarks](/topic/agent-benchmarks)), now
addressed as a deployable guard rather than only a measured risk.

**Grounding a data agent is a data-engineering investment, not just a
retrieval-technique choice**: a production case study has LangChain pairing
Hex, dbt, and a semantic-model layer with observability tooling to build a
trusted data agent, reporting a 40x increase in self-service analysis —
evidence that a governed semantic layer underneath the agent, not a better
retrieval method on top of it, is what let a fluent answer become a trusted
one (see [agent observability](/topic/agent-observability) for the
trace-and-trust side of the same build).

A second production deployment grounds the same "self-host the retrieval
stack" instinct in a sovereignty requirement rather than a data-engineering
one: OneAdvanced, a UK enterprise software provider, built a
UK-sovereign AI platform by self-hosting Llama 4 Maverick and Llama Guard 4
on Amazon SageMaker AI, with a RAG pipeline on pgvector backing more than 50
production agents. It's a concrete instance of the build-vs-buy split this
page already tracks (Orbit's self-hosted gateway) driven by a compliance
constraint — data residency — rather than cost or latency, and it pairs the
open-weight-model choice with the retrieval-architecture choice rather than
treating them separately.

## What's new
OneAdvanced built a UK-sovereign AI platform on self-hosted Llama 4
Maverick and Llama Guard 4 with a pgvector RAG pipeline backing 50+
production agents — the build-vs-buy self-hosted pattern this page already
tracks (Orbit), this time driven by data-residency compliance rather than
cost.

Prior update: A production case study (LangChain's agent-first data stack) grounds a data
agent's trustworthiness in the same structured-retrieval argument this page
already makes: pairing dbt-modeled semantic layers with observability
tooling — not a better retrieval technique alone — is what let the team
scale self-service analysis 40x.

## Why it matters for platform engineers
Grounding is the trust layer underneath every agent answer that cites a
source or claims a fact: get it wrong and the agent is fluent but
unverifiable, which is worse than an obvious failure because users don't
know to distrust it. The engineering job splits three ways — pick the
retrieval architecture (vector, graph, SQL, or a gateway spanning all
three), budget the token cost of fetching before it enters context (cross-ref
[cost](/topic/agent-cost)), and measure attribution directly rather than
assuming a fluent answer is a grounded one.
