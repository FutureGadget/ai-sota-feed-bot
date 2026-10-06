---
title: "Sentence Transformers adds off-the-shelf multi-vector (late-interaction) embedding models"
date: 2026-08-19
theme: better-retrievers
evidence: [d9524ab76177d5be]
---
Sentence Transformers now supports **multi-vector, late-interaction (ColBERT-style) models**: a query is matched against several token-level vectors per document instead of one pooled vector.

Self-hosted retrieval stacks get a packaged path to an architecture that was mostly confined to specialized research code. Expect larger indexes in exchange for finer-grained matching.
