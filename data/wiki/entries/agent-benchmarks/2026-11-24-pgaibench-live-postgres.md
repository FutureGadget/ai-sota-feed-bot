---
title: "PGAIBench tests agents on live Postgres under load, where valid SQL is not the same as safe SQL"
date: 2026-11-24
theme: own-workload
evidence: [53c219b3976d1fa6]
also: [agent-sandboxing]
---
Postgres.ai's *PGAIBench* v0.2 runs frontier models against live two-node **Postgres 18.7** clusters under concurrent load, instead of a stateless patch-and-test verifier. The failures it targets are stateful: a schema change queued behind a slow query, a config change that pauses replica recovery, an index unused on the primary but critical on a replica. The authors also propose **AAA** (Analyst, Auditor, Actor), which tests changes on a clone and separates who proposes, who reviews, and who executes.

For builders: for stateful infrastructure, grade agents on the effect against production-shaped state and traffic, and keep the actor role separate from the auditor.
