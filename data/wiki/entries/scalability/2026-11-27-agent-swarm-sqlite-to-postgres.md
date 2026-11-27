---
title: "Agent Swarm moved 24M rows from an 87 GB SQLite file to Postgres in six days, with the swarm writing the port"
date: 2026-11-27
theme: durable-state
evidence: [6f7987b91e8e3dc8]
also: [multi-agent]
---
Agent Swarm's single SQLite file reached 87 GB, and one long statement could stall the API. A swarm moved about 2,200 SQL call sites behind a storage interface, gated by a contract suite and E2E tests on both engines; it waited about 250 minutes for four human decisions. Cutover copied **24,051,347 rows** in one verified transaction, with 1h49m downtime. The first error came two minutes later: Postgres predicate-lock memory, fixed with a config change and restart. At 5x load, p99 fell from 363 ms to 51 ms while median rose from 4.7 ms to 14.7 ms.

For builders: shared, multi-process agent state outgrows one file. Build engine-parity tests before the move.
