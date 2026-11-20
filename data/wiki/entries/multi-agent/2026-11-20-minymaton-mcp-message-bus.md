---
title: "An MCP message bus with SQLite storage lets parallel coding agents post and read each other's changes"
date: 2026-11-20
theme: parallel-coding-agents
evidence: [df6b57a6e9d39c8f]
also: [mcp]
---
Minymaton is an open-source, event-driven message bus that coding agents reach over MCP, with durable SQLite storage. It targets the case where one agent changes an API, another updates its callers, and a third runs tests elsewhere, while a human relays warnings between sessions by hand. Agents publish and subscribe to channels instead.

For builders: worktrees and leases stop parallel agents from writing over each other, but they do not tell an agent what the others changed. A shared, persistent event channel fills that gap with MCP tools the agents already speak. It is an early project without published results.
