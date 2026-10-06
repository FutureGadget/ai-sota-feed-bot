---
title: "Codex adds an MCP discovery grace period and a hook to rewrite tool results"
date: 2026-08-30
theme: discovery-and-definitions
evidence: [1f2ada50b5710870]
also: [mcp]
---
Codex 0.151.0 adds a **configurable grace period for discovering tools from optional MCP servers**, and lets extensions inspect or replace an MCP tool's result before it reaches the model.

The result hook is a client-side filter on the tool-call path: a place to trim oversized payloads or redact fields without changing the server.
