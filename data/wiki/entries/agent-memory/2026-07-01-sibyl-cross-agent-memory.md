---
title: "Sibyl shares one self-hosted memory across many parallel coding agents"
date: 2026-07-01
theme: shared-memory
evidence: [23f07233dca1a9dc]
---
**Sibyl** is a self-hosted, multi-user memory system built on SurrealDB that many parallel coding agents read and write through a CLI (the author finds it works better than MCP) or MCP. It started as a Kanban board for agents with a crawler and RAG.

It reports **96.96% strict recall@5 on LongMemEval-S with no LLM in the retrieval path**: a shared, developer-owned substrate can serve many concurrent agents and stay cheap to query.
