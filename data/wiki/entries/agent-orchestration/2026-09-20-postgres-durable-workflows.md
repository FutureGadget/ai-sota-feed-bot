---
title: "Postgres alone can give agent workflows exactly-once dispatch and crash recovery"
date: 2026-09-20
theme: runtime-substrate
evidence: [a1b76774e7222dee]
also: [multi-agent]
---
An InfoQ article builds durable workflows on Postgres without an external orchestrator:
- `SELECT ... FOR UPDATE SKIP LOCKED` lets many workers poll one queue while each row is claimed by **exactly one worker**.
- A primary-key `(execution_id, step_id)` checkpoint table with `ON CONFLICT DO NOTHING` makes a rerun after a crash a no-op.
- Workers heartbeat a `lease_expires` timestamp; a sweeper re-enqueues timed-out executions.
- Sleeps and human approvals persist as rows and survive restarts.

It reportedly handles tens of thousands of steps per second on one instance for I/O-bound pipelines, on infrastructure most teams already run.
