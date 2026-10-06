---
title: "A production context-engineering stack: Redis memory, summarization, reranking, semantic caching"
date: 2026-09-04
theme: architectures
evidence: [bfa81ecf238132fd]
---
Ricardo Ferreira's talk names the concrete stack behind the tiered-memory consensus:

- **Redis** for both short-term and long-term memory
- summarization to manage token limits
- reranking and semantic caching to fight context rot
- cost controls under strict latency constraints

It is the tiered split reduced to infrastructure a team would actually run.
