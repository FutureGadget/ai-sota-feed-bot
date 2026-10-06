---
title: "Claude Code's managedMcpServers pushes approved MCP servers to every user"
date: 2026-09-04
theme: auth-and-governance
evidence: [0e371a11c328c372]
---
Claude Code v2.1.259 adds a **`managedMcpServers`** managed setting: an organization provides HTTP/SSE MCP servers to every user with the same entry shape as `.mcp.json`. Entries that name a command to run are skipped.

Governance extends from "who may connect" to "which servers exist at all", set centrally rather than per developer, and limited to remote servers.
