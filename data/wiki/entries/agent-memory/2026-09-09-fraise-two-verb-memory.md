---
title: "Fraise caps recall with a two-verb query language because the caller pays per token"
date: 2026-09-09
theme: local-first-stores
evidence: [a629cf55b03e5c2d]
---
**Fraise** is a single-binary memory database that stores facts as a temporal graph of facts, topics, and entities. It has exactly two verbs, `remember` and `recall`, for example `recall billing entity:acme since:30d top:5`.

Recall is **ranked and capped, not exhaustive**, with recent facts outranking older ones, on the stated reasoning that the caller pays for every token read back. Cost-consciousness moves from the storage format into the query interface.
