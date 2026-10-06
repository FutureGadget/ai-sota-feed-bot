---
title: "PMB pairs BM25, vectors, and an entity graph in local memory for coding agents"
date: 2026-06-23
theme: local-first-stores
evidence: [fbb59a181d9a71e6]
---
**PMB** stores memory in one SQLite file plus a local LanceDB vector index, with no server, cloud service, or API keys. Retrieval fuses **BM25, vector search, and an entity co-occurrence graph** with reciprocal rank fusion; the stated goal is the right memory, not the closest one.

It hooks the agent lifecycle over [MCP](/topic/mcp): relevant memories are injected before each response, and decisions and learnings are recorded after each turn without manual saves.
