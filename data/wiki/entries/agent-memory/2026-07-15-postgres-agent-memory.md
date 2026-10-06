---
title: "Postgres as the agent memory layer: JSONB, HNSW vectors, and row-level locking"
date: 2026-07-15
theme: shared-memory
evidence: [1609e44adca88f23]
also: [scalability]
---
Gwen Shapira's talk uses **PostgreSQL** to give agents both deterministic context (JSONB) and semantic context (high-recall HNSW vector indexes), with vector quantization speeding queries 4x, plus strategies for managing agentic memory.

For multiple agents writing shared notes and decisions, Postgres's own ACID transactions and row-level locking prevent write conflicts without a purpose-built memory service. It applies the "ride infrastructure you already run" instinct to the write-conflict problem.
