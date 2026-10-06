---
title: "Enjambre packages a durable queue, leases, and a router into one SQLite kernel for agent swarms"
date: 2026-09-20
theme: runtime-substrate
evidence: [7292eba504d2de73]
also: [multi-agent]
---
Enjambre is a SQLite-backed "kernel" for agent swarms: a durable task queue with DAG dependencies, **atomic claims with idempotency keys, auto-expiring leases** (liveness derived from heartbeat age), and dead-letter states that record why a task failed. On top sit a permission gate that enforces rules before an agent runs and a router that picks agents by success rate, latency, and cost. MCP tools (`enqueue_task`, `claim_task`, `complete_task`) let any MCP client drive the queue.

It is very early (about ten commits, no adoption signal), but it ships the Postgres recipe's guarantees as one deployable unit.
