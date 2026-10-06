---
slug: rag-retrieval-scaling
title: "Why does RAG accuracy degrade as the knowledge base grows, and what fixes it?"
question: "Why does RAG accuracy degrade as the knowledge base grows, and what fixes it?"
summary: "Naive top-k vector retrieval treats every chunk as an independent nearest-neighbor hit, so as a knowledge base grows, questions needing several chunks combined get harder to answer in one shot. The fix is structural (graphs, agentic re-retrieval, precomputed task views), not a bigger k."
status: active
cluster: retrieval
updated: 2026-10-06
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
    added: 2026-08-05
    note: "Introduces the RAG mechanism this space builds on: a dense retriever fetches the top-k passages by vector similarity, and the generator conditions on them. Retrieval and generation are separate stages, so the generator can only use what similarity search surfaced."
  - id: edge-2024-graphrag
    kind: theory-paper
    title: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"
    url: "https://arxiv.org/abs/2404.16130"
    added: 2026-08-05
    note: "Shows flat top-k retrieval fails on questions that connect facts across many documents, such as query-focused summarization over a whole corpus. Builds an entity/relationship graph and community summaries offline so a query traverses structure instead of depending on one chunk's vector coming back as the top hit."
  - id: story-355c8cf2c3a4e36a-agentic-rag-survey
    kind: story
    sid: 355c8cf2c3a4e36a
    title: "Towards Trustworthy and Cost-Efficient Data Integration: From Naïve RAG to Agentic RAG"
    added: 2026-08-05
    note: "Survey tracing naive RAG to GraphRAG/KG-RAG to Agentic RAG from a data-integration angle. In Agentic RAG a multi-agent loop plans, retrieves, refines, and re-reasons instead of taking one retrieval pass as final, in response to accuracy and cost problems in enterprise deployments."
  - id: story-46be0149e39dc713-aws-takc
    kind: story
    sid: 46be0149e39dc713
    title: "Beyond RAG: Task-aware knowledge compression for enterprise AI on AWS"
    added: 2026-08-05
    note: "Vendor post reporting that flat RAG hits a ceiling on analytical tasks spanning hundreds of documents. Describes pre-compressing a knowledge base into task-specific representations at multiple fidelity tiers and routing each query to the tier with enough context, moving structuring work from query time to index time. No independent benchmark."
  - id: rag-scaling-editorial-synthesis
    kind: editorial-inference
    title: "One fix does not cover every degradation mode"
    added: 2026-08-05
    note: "Editorial synthesis: graph structure, an agentic retrieve-and-check loop, and task-aware pre-compression are not interchangeable. They target different symptoms (missing cross-document links, under-coverage on complex questions, per-query cost), and a system can need more than one. No source here claims one fix supersedes the others."
---

## Builder consequence
A RAG demo on a few hundred documents can look solid, then get worse every month as the knowledge base grows, because retrieval was never the part that scales. If production misses cluster on questions needing two or more facts stitched together, that is not a prompting or model-size problem. Flat top-k similarity search has hit its structural ceiling, and the fix belongs before generation.

## Short answer
Naive RAG makes one independent top-k similarity lookup per query. As the corpus grows, the odds that every fact a multi-document question needs lands in that one window shrink. Three structural fixes attack this from different sides:

- **Graph retrieval (GraphRAG/KG-RAG):** precompute entities and relationships so a query traverses links.
- **Agentic RAG:** plan, retrieve, check coverage, and retrieve again when needed.
- **Task-aware compression:** precompute task-specific summaries at several fidelity tiers and route each query to one.

Each moves structuring work ahead of the similarity search.

## Builder model
Flat vector RAG answers "what single chunk is most similar to this question," not "what set of chunks together answers it." A one-chunk question stays reliable at any corpus size. A question needing two or three chunks requires all of them to land in the same top-k window, which gets harder as more distractor chunks compete for the k slots.

The three fixes are different levers on that problem:

- **GraphRAG:** "search once over flat chunks" becomes "traverse precomputed structure."
- **Agentic RAG:** "search once" becomes "search, check, search again."
- **Task-aware compression:** "search the raw corpus at query time" becomes "search a smaller, pre-digested, task-specific index."

They combine; you do not have to pick exactly one.

## Mechanism
**Baseline.** Standard RAG (Lewis et al., 2020) embeds the query, retrieves the k nearest passages, and conditions generation on them. The generator sees only what similarity search surfaced and cannot ask for more.

**GraphRAG** (Edge et al., 2024) targets corpus-spanning questions, such as "what are the major themes across these documents," where no single chunk is the answer. It builds an entity and relationship graph offline, clusters it into communities, and precomputes a summary per community. A query combines relevant community summaries instead of hoping one vector hit contains everything.

**Agentic RAG** turns retrieval into a loop: plan what is needed, retrieve, check whether the context covers the question, and retrieve again (possibly reformulated) if not. A pass that misses one of three needed facts gets a second chance instead of silently generating from incomplete context.

**Task-aware compression** (the AWS "Beyond RAG" pattern) pre-compresses the knowledge base into task-specific representations at multiple fidelity tiers, caches them, and routes each query to the tier with enough context for its task shape. It trades index-build cost and staleness risk for lower per-query cost and a ceiling that does not depend on top-k luck.

## Math intuition
Take a question needing `m` facts, each in a different chunk, a corpus of `n` chunks, and a retrieval budget `k`. Each needed chunk's odds of landing in the top-k window shrink as `n` grows relative to `k`. If those odds are roughly independent, the chance that *all* `m` land together is roughly their product.

- One-fact questions degrade slowly as the corpus grows.
- Three- or four-fact questions degrade much faster, because missing any one breaks the answer.

So RAG does not decline uniformly with corpus size. Multi-hop, cross-document questions fail first, which is exactly what each structural fix targets.

## How to apply
- **Characterize failures first.** Misses on one-fact questions point to chunking or embedding quality. Misses on multi-fact questions are the structural coverage problem.
- **Do not just raise `k`.** It adds distractors without improving the odds that the right combination lands together.
- **Corpus-wide or cross-document misses:** try GraphRAG-style precomputed structure first.
- **"A second, reformulated query would have caught it" misses:** use an agentic retrieve-and-check loop, and budget for its extra latency and cost per query.
- **Cost or latency at scale is the pain:** use task-aware pre-compression, which only pays off when task shapes are stable enough to precompute.
- **Fine-tune only for narrow, repeated query distributions** where an index costs more than baking knowledge into weights. Keep a multi-hop coverage eval either way; fine-tuning does not fix a structural retrieval gap.

## Failure modes
- **Raising `k` without restructuring:** more competing chunks, no better coverage, and relevant chunks pushed out of the generator's effective attention.
- **A graph built once and never refreshed:** changed entities and relationships silently misdirect traversal.
- **An agentic loop with no stop condition or coverage eval:** unbounded retrieval rounds and an easy-to-miss cost and latency tax.
- **Compression tiers cached without invalidation:** stale summaries served with high confidence, worse than a cache miss that falls back to fresh retrieval.

## Related
See [/topic/vector-kb](/topic/vector-kb) for the retrieval baseline (vector vs. graph indexes) and [/topic/grounding](/topic/grounding) for why an answer is only as trustworthy as what was retrieved.
