---
title: "Memharness keeps bi-temporal agent memory in one SQLite file"
date: 2026-06-20
theme: beyond-vectors
evidence: [623de2bad771dca8]
---
Memharness stores agent memory **bi-temporally in a single SQLite file**: each fact records when it was true and when it was recorded, so recall leans on time and structure instead of embeddings.

For questions like "what did we believe last Tuesday", a relational store with time columns gives an exact answer that similarity search cannot, and it runs with no separate service to operate.
