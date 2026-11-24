---
title: "About 8,000 agent-memory MCP repos exist; most have zero stars and stall within a month"
date: 2026-11-24
theme: local-first-stores
evidence: [da091c806052aac1]
also: [mcp]
---
A GitHub census estimates about **7,970** agent-memory MCP servers, from a hand-labeled sample of 200. Most reuse the same three storage backends, sit at zero stars, and stop receiving pushes within a month. The 13 high-star memory projects that ship an MCP server hold **506,637** stars between them. The author's argument: standalone memory products lose to hosts and harnesses that ship memory directly.

For builders: picking a small memory MCP server adds a dependency that may be unmaintained next month. Prefer your harness's built-in memory or one of the few maintained projects, and keep the data in a store you already operate.
