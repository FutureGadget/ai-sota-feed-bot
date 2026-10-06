---
title: "Langfuse v4 stores traces and eval results in one immutable ClickHouse table"
date: 2026-08-19
theme: storage
evidence: [f49b38f16a2b7158]
---
Langfuse v4 rebuilds both **agent traces and evaluation results onto one immutable ClickHouse table**, collapsing what were separate storage paths into one queryable store.

A score can now be joined back to the run that produced it without crossing systems. It is the same infrastructure hardening as LangSmith's SmithDB, aimed at unifying capture and evaluation rather than indexing traces alone.
