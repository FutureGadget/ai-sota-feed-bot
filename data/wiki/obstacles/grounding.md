---
slug: grounding
kind: obstacle
title: "An agent's answer is only as good as what it retrieved — and whether it can prove it"
area: grounding
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1, 20a176e41161c528, 46be0149e39dc713, 5ca9aca0e46db978, 355c8cf2c3a4e36a, 5f80558cf12e2ddc, aec50bce133680e8, d9524ab76177d5be, 7b2b4d44ea281840, 5a50cd46503b235d, a6a23d3dd800c218, 24ddbe91a622a3cd, 149a211377f80efa, a74f114f24afad46, 55636c14f8cd3609, a7ea832bc7e9c508, 4be01fb545d6c7c4]
updated: 2026-09-04
covers_evidence: [95730baaa42549c2, 1609e44adca88f23, c74bb13bcd038d10, cfe2e766a965b837, 12c546b2fc140ca1, 980d749ecfc6165f, ace88b2c5ecc23e1, 20a176e41161c528, 46be0149e39dc713, 5ca9aca0e46db978, 355c8cf2c3a4e36a, 5f80558cf12e2ddc, aec50bce133680e8, d9524ab76177d5be, 7b2b4d44ea281840, 5a50cd46503b235d, a6a23d3dd800c218, 24ddbe91a622a3cd, 149a211377f80efa, a74f114f24afad46, 55636c14f8cd3609, a7ea832bc7e9c508, 4be01fb545d6c7c4]
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

**Retrieved content verification is arriving as dedicated middleware**, not
just a scoring metric: an Evaluation Agent layered over a RAG pipeline
combines natural-language-inference fact-checking with a five-signal poison
detector and a weighted Trust Index (0.4x factuality + 0.35x coherence +
0.25x(1-poison), with a non-linear dampener for high-contamination contexts)
to catch documents that read as relevant but are false or adversarially
inserted. On TruthfulQA it reaches 91% accuracy and 100% recall on
instruction-injection attempts, though in-place edits like entity swaps
stay hard to catch, and cross-dataset generalization (FEVER) needs
per-model threshold recalibration rather than transferring as-is —
grounding a knowledge-poisoning defense in scored, checkable middleware
rather than trusting the retriever's ranking alone (cross-ref [prompt
injection](/topic/prompt-injection) for the attack side of the same threat).

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

**Structured extraction now also targets the numbers hiding inside a chart**,
not just the surrounding caption: Databricks parses chart figures into
structured JSON (via `ai_parse_document`) and embeds that JSON-enriched chunk
instead of caption text alone, indexed with a lightweight 300M-parameter
embedding model. On the chart-heavy ViDoRe V3 benchmark (310 questions) this
reaches 75.9% answer correctness with only the top-3 retrieved images, and
75.1% on a synthetic Chart-RAG set — beating four larger multimodal embedding
baselines while passing the agent fewer images, evidence that a small model
over structured content can out-retrieve a bigger one over raw pixels. It's
the same structured-recall argument this page already makes for SQL over
embeddings and OKF front matter over open-ended doc search, this time applied
to the figures inside enterprise documents.

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

**The retriever's own architecture options keep widening**, distinct from the
vector/graph/SQL/gateway split above: Sentence Transformers added
off-the-shelf support for multi-vector, late-interaction (ColBERT-style)
embedding models — matching a query against several token-level vectors per
document instead of one pooled vector — giving self-hosted retrieval stacks a
packaged path to a retrieval architecture previously mostly confined to
specialized research implementations, the same "the retriever itself keeps
improving" thread this page already tracks for Nemotron 3 Embed above.

**Multimodal embedding models are catching up to the same "retriever keeps
improving" trend**, extending it past text: Tencent's WeMM-Embedding-9B,
built on Qwen3.5, embeds text, images, video, and visual documents into a
single 4,096-dimension space and scores 80.6 average on MMEB-v2 (78
datasets) — ahead of Qwen3-VL-Embedding's 77.8 — and 59.5 on the newer,
harder MMEB-v3 (190 tasks spanning text, agent, and multimodal retrieval). A
retriever that natively embeds slide decks and chart-bearing pages, rather
than requiring a separate structured-extraction pass, has the same
ceiling-raising effect on multimodal grounding that Nemotron 3 Embed has on
text retrieval above — reaching the same documents the chart-extraction
paragraph above is chasing with a different technique.

**Adversarial grounding gets a second defense mechanism**, distinct from
Salience Normalization above: DSPrompt proposes a dynamic soft-prompt
defense against multimodal-RAG (M-RAG) corruption, where an attacker crafts
embeddings that align with benign entries in the retrieval vector space to
get poisoned content surfaced as if it were relevant — the same
retrieval-ordering attack surface Salience Induction already demonstrates,
this time targeting the embedding space directly rather than fact salience.

**Recovering evidence through a bounded interface, not just ranking it, is
its own open problem**: CABLE studies why an agent operating across
long-running sessions can fail to recover relevant evidence even when a
fact was stored earlier, because the interface a bounded context provides
limits what later steps can retrieve — proposing complementary
antecedent-based linking to widen that interface rather than assuming more
storage alone fixes recall (cross-ref [agent memory](/topic/agent-memory)
for the storage side of the same gap).

Incumbent datastores keep adding native vector search as a retrieval option
on top of data they already hold: DynamoDB shipped a `SearchVectors` API
for approximate nearest-neighbor lookups alongside application rows (see
[vector-kb](/topic/vector-kb) for the full incumbent-datastore trend).

**The gateway pattern is now arriving as a managed platform service, not
just a self-hosted toolkit**: Cloudflare AI Search runs the full retrieval
pipeline — crawl, parse, embed, retrieve — as one built-in service exposing
a single search endpoint over a custom data collection, with a "discover"
mode that finds and indexes pages without requiring the site to publish a
sitemap first, and public `/mcp` and `/search` endpoints so an agent or MCP
client can query it without touching the underlying store. It's the same
"which store, which query language" consolidation Orbit's self-hosted
gateway already makes above, this time as a hosted service a platform
engineer doesn't have to run themselves, trading self-hosting control for
setup speed.

**A fourth grounding attack targets evidence that is factually true but
answers the wrong question**: Lazy Grounding tests search agents with
rewritten queries paired with documents that truthfully support the
rewritten version but still surface for the original one, and finds this
"nearby but wrong" evidence drags accuracy down 5.9 points on average and up
to 17.3 points across 12 model-benchmark combinations — a retrieval-quality
failure distinct from Salience Induction's truth-preserving reordering and
DSPrompt's embedding-space poisoning above, because nothing in the retrieved
document is false or adversarially inserted, it just answers a
plausible-looking neighbor of the actual question. On the defense side,
SCoNE answers the standing "retrieved documents mix informative and
irrelevant context, and the model gets distracted" problem with a
training-free fix: it identifies context-aware FFN neurons by both high
attribution and high cross-input variability, then selectively strengthens
just those neurons at inference time — no fine-tuning, no added inference
latency, and only a small calibration sample — reporting consistent gains
over baseline RAG methods across multiple knowledge-intensive QA benchmarks
and two model backbones.

## What's new
Lazy Grounding shows search agents can be misled by evidence that is
factually accurate but answers a rewritten neighbor of the actual query,
cutting accuracy 5.9 points on average (up to 17.3) across 12
model-benchmark pairs — a distinct failure mode from the truth-preserving
reordering and embedding-poisoning attacks this page already tracks. SCoNE
answers the standing retrieval-noise problem with a training-free fix:
selectively strengthening context-aware FFN neurons at inference time, with
no fine-tuning or added latency (see State of the art above).

Prior update: Cloudflare AI Search packages the full retrieval pipeline (crawl, parse,
embed, retrieve) as a managed service with a single search endpoint and
public `/mcp`/`/search` access, plus a "discover" mode that indexes sites
without a published sitemap — the gateway-consolidation pattern this page
already tracks (Orbit), now available as a hosted platform service instead
of only a self-hosted toolkit (see State of the art above).

Prior update: Databricks extracts chart figures into structured JSON (via
`ai_parse_document`) instead of relying on captions alone, then indexes the
JSON-enriched chunks with a lightweight 300M-parameter embedding model. On
the chart-heavy ViDoRe V3 benchmark it reaches 75.9% answer correctness with
only the top-3 retrieved images, beating four larger multimodal embedding
baselines — closing the blind spot pure text/caption retrieval leaves for
the numbers inside enterprise charts.

Prior update: Tencent's WeMM-Embedding-9B extends the "retriever keeps
improving" trend to multimodal grounding, embedding text, images, video, and
visual documents into one space and scoring 80.6 on MMEB-v2 (78 datasets) —
ahead of Qwen3-VL-Embedding's 77.8.

## Why it matters for platform engineers
Grounding is the trust layer underneath every agent answer that cites a
source or claims a fact: get it wrong and the agent is fluent but
unverifiable, which is worse than an obvious failure because users don't
know to distrust it. The engineering job splits three ways — pick the
retrieval architecture (vector, graph, SQL, or a gateway spanning all
three), budget the token cost of fetching before it enters context (cross-ref
[cost](/topic/agent-cost)), and measure attribution directly rather than
assuming a fluent answer is a grounded one.
