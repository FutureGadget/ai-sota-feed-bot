---
slug: rag-retrieval-scaling
title: "Why does RAG accuracy degrade as the knowledge base grows, and what fixes it?"
question: "Why does RAG accuracy degrade as the knowledge base grows, and what fixes it?"
summary: "Naive top-k vector retrieval treats every chunk as an independent nearest-neighbor hit, so as a knowledge base grows, questions that need two or more chunks combined become steadily less likely to get everything they need in one shot — the fix is structural (graph traversal, an agentic retrieve-and-check loop, or precomputed task-specific views), not a bigger k."
status: active
cluster: retrieval
updated: 2026-08-05
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [vector-kb, grounding]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: lewis-2020-rag
    kind: theory-paper
    title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
    url: "https://arxiv.org/abs/2005.11401"
    note: "Introduces the RAG mechanism this whole space builds on: a dense retriever fetches the top-k passages by vector similarity, and the generator conditions on them. Retrieval and generation are separate stages — the generator can only use what similarity search happened to surface."
  - id: edge-2024-graphrag
    kind: theory-paper
    title: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"
    url: "https://arxiv.org/abs/2404.16130"
    note: "Shows flat top-k retrieval fails on questions that require connecting facts spread across many documents (query-focused summarization over a whole corpus). Builds an entity/relationship graph and community summaries ahead of time so a query traverses structure instead of relying on any single chunk's vector coming back as the top hit."
  - id: story-355c8cf2c3a4e36a-agentic-rag-survey
    kind: story
    sid: 355c8cf2c3a4e36a
    title: "Towards Trustworthy and Cost-Efficient Data Integration: From Naïve RAG to Agentic RAG"
    note: "Traces the same progression from a production angle: naive RAG to GraphRAG/KG-RAG to Agentic RAG, where a multi-agent loop adaptively plans, retrieves, refines, and re-reasons instead of taking one retrieval pass as final."
  - id: story-46be0149e39dc713-aws-takc
    kind: story
    sid: 46be0149e39dc713
    title: "Beyond RAG: Task-aware knowledge compression for enterprise AI on AWS"
    note: "Reports that flat RAG hits a ceiling on analytical tasks spanning hundreds of documents, and describes pre-compressing a knowledge base into task-specific representations at multiple fidelity tiers, then routing each query to the tier with enough context — moving structuring work to index time instead of query time."
  - id: rag-scaling-editorial-synthesis
    kind: editorial-inference
    title: "One fix does not cover every degradation mode"
    note: "Editorial synthesis: graph structure, an agentic retrieve-and-check loop, and task-aware pre-compression are not interchangeable fixes for the same failure. They target different symptoms — missing cross-document links, under-coverage on complex questions, and per-query compute cost — and a system can need more than one at once."
covers_evidence:
  - lewis-2020-rag
  - edge-2024-graphrag
  - story-355c8cf2c3a4e36a-agentic-rag-survey
  - story-46be0149e39dc713-aws-takc
  - rag-scaling-editorial-synthesis
---

## Builder consequence
A RAG demo built on a few hundred documents can look solid, then quietly get worse every month as the knowledge base grows — not because the model got dumber, but because the retrieval step was never the part that scales. If your production RAG's misses cluster on questions that need two or more facts stitched together, that's not a prompting problem or a bigger-model problem. It's a sign that flat top-k similarity search has hit its structural ceiling, and the fix is to change what happens before generation, not to tune the generation step further.

## Short answer
Naive RAG retrieves the top-k chunks by vector similarity and hands them to the generator, one independent lookup per query. As the corpus grows, the odds that every fact a question needs lands in that single top-k window shrink, especially for questions that require combining facts from multiple documents. Three structural fixes address this from different angles: graph-based retrieval (GraphRAG/KG-RAG) precomputes entity and relationship structure so a query can traverse links instead of depending on one lucky vector match; agentic RAG replaces the one-shot lookup with a loop that plans, retrieves, checks coverage, and retrieves again when it isn't enough; task-aware compression precomputes task-specific summaries at multiple fidelity tiers ahead of query time and routes each query to the tier that already has what it needs. None of these make the underlying model retrieve better per se — they change how much structuring work happens before a similarity search ever runs.

## Builder model
Think of flat vector RAG as a single independent nearest-neighbor lookup per query: it answers "what's the most similar chunk to this question," not "what set of chunks, together, answers this question." A question answerable from one chunk stays reliable at any corpus size. A question that requires two or three chunks in combination becomes a search for all of them landing in the same top-k window at once — a much harder ask, and one that gets harder as the corpus grows and more distractor chunks compete for those k slots.

GraphRAG replaces "search once over flat chunks" with "traverse precomputed structure." Agentic RAG replaces "search once" with "search, evaluate whether that's enough, and search again if it isn't." Task-aware compression replaces "search the raw corpus at query time" with "search a smaller, pre-digested, task-specific index built ahead of time." They are different levers on the same problem, not competing solutions to pick exactly one of.

## Mechanism
Standard RAG (Lewis et al., 2020) embeds a query, retrieves the k nearest passage vectors from an index, and conditions generation on those k passages. The retriever and generator are separate: the generator only ever sees what similarity search happened to surface, and gets no chance to ask for more.

**GraphRAG** (Edge et al., 2024) targets query-focused questions that span a whole corpus rather than one passage — "what are the major themes across all these documents" has no single chunk that is the answer. It builds an entity and relationship graph from the corpus offline, clusters that graph into communities, and precomputes a summary per community. A query then traverses the graph and combines relevant community summaries, rather than hoping one vector search returns a chunk that happens to contain the whole answer.

**Agentic RAG** turns retrieval from a single pass into a loop: plan what's needed, retrieve, evaluate whether the retrieved context actually covers the question, and issue another retrieval (possibly reformulated) if it doesn't. This directly targets the coverage problem — a single top-k pull missing one of three needed facts gets a second chance instead of silently generating from an incomplete context.

**Task-aware compression** (the AWS "Beyond RAG" pattern) moves structuring work to index time instead of query time: it pre-compresses the knowledge base into compact, task-specific representations at multiple fidelity tiers, caches them, and routes each incoming query to the tier that already has enough context for that task shape. It trades index-build cost and staleness risk for lower per-query retrieval cost and a ceiling that doesn't depend on getting lucky with top-k.

## Math intuition
Model a question that needs `m` distinct facts, each living in a different chunk, with a flat corpus of `n` chunks and a fixed retrieval budget of `k`. Treat each needed chunk's odds of landing in the top-k window as roughly independent and shrinking as `n` grows relative to `k` (more chunks compete for the same k slots). The odds that *all* `m` needed chunks land in the same top-k window is then roughly the product of each chunk's individual odds — a number that falls off multiplicatively in `m`, not additively. A question needing one fact degrades slowly as the corpus grows; a question needing three or four facts degrades much faster, because missing any single one breaks the whole answer. That is the concrete shape of "RAG gets worse as the corpus grows": it isn't a uniform decline, it's a decline that hits multi-hop, cross-document questions hardest first — which is exactly the failure mode GraphRAG, agentic re-retrieval, and task-aware compression each independently target.

## Evidence
Lewis et al. (2020) establishes the retrieve-then-generate mechanism that every variant here modifies (theory-paper). Edge et al. (2024)'s GraphRAG paper demonstrates the specific failure mode — corpus-spanning, query-focused questions — that flat top-k retrieval cannot answer, and the graph-traversal fix (theory-paper). The agentic-RAG survey traces the same naive-to-graph-to-agentic progression from a data-integration production angle, describing the retrieve-refine-reason loop as the response to persistent accuracy and cost problems in enterprise deployments (story). The AWS task-aware compression post reports the same ceiling from a different production context — analytical tasks spanning hundreds of documents — and describes an implemented pre-compression-and-routing fix (story). No single source in this set claims one fix supersedes the others; treat them as evidence for three separate, compatible levers on the same underlying problem (editorial inference).

## How to apply
Before reaching for any fix, characterize your retrieval failures: pull the queries your RAG system gets wrong and check whether they cluster on questions needing one fact (rare miss, probably a chunking or embedding-quality issue) versus questions needing several facts combined (structural coverage problem, the one this page addresses). Don't respond to the second pattern by just raising `k` — that adds distractor chunks competing for the generator's attention without improving the odds that the *right* combination of chunks all land together.

If failures cluster on corpus-wide or cross-document questions, evaluate GraphRAG-style precomputed structure first — it's the most direct match for "no single chunk contains the answer." If failures look more like "the first retrieval pass just wasn't enough and a second, reformulated query would have caught it," an agentic retrieve-and-check loop is the better-targeted fix, but budget for its added latency and cost per query since it can issue multiple retrieval rounds. If the real pain is retrieval cost or latency at scale rather than coverage, task-aware pre-compression is the lever — it moves cost from query time to index-build time, which only pays off if your task shapes are stable enough to precompute for.

Reach for fine-tuning instead of any of these only when the query distribution is narrow and repeated enough that maintaining a retrieval index costs more than baking the knowledge into weights — and even then, keep an eval that separately measures multi-hop coverage, because fine-tuning doesn't fix a structural retrieval gap either.

## Failure modes
Raising `k` without restructuring adds noise, not coverage — more competing chunks in the context window, no better odds the needed combination is among them, and a real risk of pushing genuinely relevant chunks out of the generator's effective attention. A knowledge graph built once and never refreshed goes stale exactly where GraphRAG's advantage matters most: entities and relationships that changed since the last build silently misdirect traversal instead of failing loudly. An agentic retrieve-and-check loop with no stop condition or coverage eval can spiral into unbounded extra retrieval rounds, trading an unpredictable and easy-to-miss cost and latency tax for marginal coverage gains. Task-aware compression tiers cached without an invalidation path serve stale pre-digested summaries once the source documents change, which is worse than a plain cache miss because the system reports high confidence in an outdated answer instead of falling back to fresh retrieval.

## Related
See `/topic/vector-kb` for the retrieval-mechanism baseline (vector vs. graph indexes) and `/topic/grounding` for why an agent's answer is only as trustworthy as what it retrieved and can prove it retrieved.
