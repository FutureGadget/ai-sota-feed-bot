---
title: "FERNme builds graph memory with ~zero LLM calls using a Hebbian co-occurrence rule"
date: 2026-06-22
theme: local-first-stores
evidence: [eb5267262e7d31c8]
---
**FERNme** is a graph-based associative memory that forms memory tags from fuzzy edges and a **Hebbian co-occurrence rule**, updating with roughly zero LLM calls.

It is the cheap-writes pattern: build the memory structure deterministically instead of asking a model what to store each turn, so persisting what an agent learns stops being a per-turn token bill.
