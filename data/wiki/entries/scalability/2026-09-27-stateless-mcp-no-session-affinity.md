---
title: "Stateless MCP removes sticky sessions, so remote MCP servers scale like any stateless service"
date: 2026-09-27
theme: coordinator-free-scheduling
evidence: [14ca1514017a2ee2]
---
AWS details how the latest MCP specification removes **protocol-level sessions, sticky-session requirements, and session storage** for remote MCP servers. Requests can route independently, so servers scale horizontally behind an ordinary load balancer.

It is the same "remove the coordinator" move Modal made for sandbox scheduling, applied to the tool-calling protocol. The state does not disappear: application state, retries, observability, and idempotency move to other layers that you now own. See [MCP](/topic/mcp) for the full protocol change.
