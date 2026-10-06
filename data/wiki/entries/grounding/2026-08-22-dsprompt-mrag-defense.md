---
title: "DSPrompt defends multimodal RAG against poisoned embeddings that mimic benign entries"
date: 2026-08-22
theme: adversarial-evidence
evidence: [a6a23d3dd800c218]
---
In multimodal RAG, attackers craft data whose **embeddings align with benign entries** in the vector space, so poisoned content is retrieved as if relevant. Existing query-time defenses (auxiliary detectors, similarity re-ranking, consistency checks) add inference overhead and generalize poorly. **DSPrompt** proposes a dynamic soft-prompt defense instead.

The attack targets the embedding space directly, so retriever ranking alone cannot be trusted as a relevance signal on untrusted corpora.
