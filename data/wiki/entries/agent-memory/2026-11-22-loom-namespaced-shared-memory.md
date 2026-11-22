---
title: "ClickHouse Loom shares memory across coding agents through namespace-scoped read and write tokens"
date: 2026-11-22
theme: shared-memory
evidence: [e76fa817c2806f1f]
also: [mcp]
---
ClickHouse open-sourced Loom, a self-hosted MCP server that gives Claude Code, Codex, Cursor, and custom agents one long-term memory. In team mode **each agent holds a token scoped to namespaces with read or write roles**, so what one agent learns is visible to the next without opening every namespace to every agent. Memories link to the files and symbols they describe, follow them through refactors, and are flagged when that code changes. Storage is ClickHouse, with Postgres as an option for live memory state.

Vendor-reported results: **98.6%** LongMemEval-S evidence retrieval in the top 30 memories, and 92.0% answer accuracy with a fixed `gpt-5` reader. For builders: shared memory needs the same per-principal access control as any datastore, not one global namespace.
