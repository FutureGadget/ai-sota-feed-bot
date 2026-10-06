---
title: "OKF Agent Memory stores git-tracked Markdown to Google's Open Knowledge Format spec"
date: 2026-09-07
theme: local-first-stores
evidence: [44a795850e3c5a06]
---
**OKF Agent Memory** keeps facts, decisions, and domain concepts as git-tracked Markdown with YAML front matter, implementing Google's **Open Knowledge Format v0.2**, which bakes in provenance, trust tiers, and lifecycle metadata.

Retrieval is in-memory BM25 with no vector database or embedding cost, returning in under 300 microseconds. A progressive-disclosure index lets the agent pull one concept at a time, cutting token use roughly 80% versus loading the whole knowledge base. It is the zero-LLM pattern built to a vendor-neutral spec.
