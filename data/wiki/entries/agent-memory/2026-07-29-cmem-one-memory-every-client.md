---
title: "CMEM shares one local memory across Cursor, Claude Code, and CLI agents with sub-second recall"
date: 2026-07-29
theme: shared-memory
evidence: [7b8e28ef4195d912]
---
**CMEM** pairs a local SQLite store of timestamped observations (decisions, dead ends, fixes, not just diffs) with a built-in vector index. One MCP server exposes it to every client, so Cursor, Claude Code, and a bare CLI agent share the same memory, with recall reported **under one second**.

It bundles 11 skills so teams don't write the write/recall logic themselves (the vendor cites 6+ weeks for a custom build). It is Apache-2.0 and self-hosted, with an optional paid cloud mirror for cross-device sync.
