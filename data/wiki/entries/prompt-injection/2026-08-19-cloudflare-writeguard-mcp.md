---
title: "Cloudflare WriteGuard adds fine-grained controls over MCP tools that modify data"
date: 2026-08-19
theme: agent-authorization
evidence: [e3560887ce822a61]
---
Cloudflare's WriteGuard, in private beta, adds fine-grained security controls for MCP servers. It governs agents' access to **tools that modify data or take actions**, not only tools that read.

The read/write split is where injection does damage. Gating write tools at the MCP layer applies least privilege per tool without relying on each connector's own auth conventions. See [MCP](/topic/mcp).
