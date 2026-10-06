---
title: "Langfuse v4 rebuilds agent evals and traces on one immutable ClickHouse table"
date: 2026-08-19
theme: eval-in-production
evidence: [f49b38f16a2b7158]
---
**Langfuse v4** stores agent evals and traces on **one immutable ClickHouse table**.

Putting scores and spans in the same store makes "join this eval result to the trace that produced it" a query rather than an integration — the storage-level version of the eval/tracing convergence.
