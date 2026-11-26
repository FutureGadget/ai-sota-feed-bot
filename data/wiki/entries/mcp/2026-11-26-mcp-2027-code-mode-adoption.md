---
title: "MCP's case for 2027: Code Mode plus typed outputSchema, with large reported production call volumes"
date: 2026-11-26
theme: servers-in-production
evidence: [93cec7f36fc5907a]
also: [tool-use]
---
Philipp Schmid argues the context-bloat backlash against MCP is fading, and cites company-reported volumes: Atlassian handles over **5M MCP tool calls per workday**, **44%** from users outside software teams; Notion reports **60x** MCP traffic growth; Neon's MCP agent usage grows **14% week over week**.

The technical shift is *Code Mode*. Instead of loading dozens of tool schemas and calling one tool per turn, the harness exposes MCP tools as functions in a sandbox. When a server declares `outputSchema`, the client generates typed stubs, so the model chains, filters, and joins calls in one script and returns only the result.

For builders: declare `outputSchema` on servers you own. It is what lets Code Mode clients keep intermediate payloads out of context.
