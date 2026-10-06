---
title: "MemRefine compresses a long-term memory store to fit a hard storage budget"
date: 2026-06-18
theme: curating-the-working-set
evidence: [10129892c7fcda0f]
also: [agent-memory]
---
MemRefine frames **storage-budgeted memory management**: keep an already-built memory store within a fixed budget using LLM-guided compression. As interactions accumulate, the store grows without bound and fills with redundant entries that inflate storage cost and crowd out the most useful evidence at retrieval time.

Compaction is not only for the live context window. A persistent store needs the same pruning, especially on resource-constrained platforms with hard memory limits.
