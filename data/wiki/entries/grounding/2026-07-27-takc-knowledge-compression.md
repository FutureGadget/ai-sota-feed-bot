---
title: "AWS TAKC pre-compresses a whole knowledge base into task-specific tiers ahead of query time"
date: 2026-07-27
theme: context-budget
evidence: [46be0149e39dc713]
---
AWS describes **task-aware knowledge compression (TAKC)** for analytical questions that span hundreds of documents, where plain RAG hits a ceiling. It pre-compresses the knowledge base into task-specific representations, caches them at **multiple fidelity tiers**, and routes each query to the right tier. An open-source implementation is included.

It trades an up-front compression pass for a smaller, denser context at answer time, instead of retrieving and re-reading raw pages per query.
