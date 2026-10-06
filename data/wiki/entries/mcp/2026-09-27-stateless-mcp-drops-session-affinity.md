---
title: "Stateless MCP lets remote servers drop sticky sessions and scale horizontally"
date: 2026-09-27
theme: stateless-spec
evidence: [14ca1514017a2ee2]
---
AWS details how the current spec **removes protocol-level sessions, sticky-session requirements, and session storage** for remote MCP servers. Each request routes independently, so a server scales like any other stateless service.

Application state, retries, observability, and idempotency move to the layers that already handle them for other APIs. See [scalability](/topic/scalability) for the same "remove the coordinator" pattern.
