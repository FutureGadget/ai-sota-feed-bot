---
title: "Orbit packages file RAG, multi-backend vector RAG, and NL-to-query into one self-hosted gateway"
date: 2026-07-15
theme: retrieval-architecture
evidence: [95730baaa42549c2]
---
Orbit is an open-source toolkit for retrieval-based inference that bundles file RAG, vector RAG across **Chroma, Qdrant, Pinecone, Weaviate, pgvector, and FAISS**, and natural-language-to-query translation over SQL, NoSQL, and REST sources.

"Which store, which query language" becomes a routing decision inside one gateway instead of a separate integration per source. That is the build-it-yourself end of the gateway pattern.
