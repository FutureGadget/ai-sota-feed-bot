---
title: "Databricks Agent Memory keeps raw sessions plus a background-distilled memory layer on Postgres"
date: 2026-10-20
theme: local-first-stores
evidence: [71440eae5c3aaa1a]
---
Databricks released Agent Memory in Beta on Lakebase (serverless Postgres), built on its MemCurrent design: managed **sessions** hold the raw record, and a background pipeline extracts durable facts, deduplicates, and replaces facts that newer conversations contradict. Agents load a memory index at session start and search by hybrid keyword and semantic retrieval.

Vendor-reported internal results: about 3x the pass rate on enterprise tasks with 31% fewer tokens, and one repeat query dropped from 11 tool calls and nearly six minutes to 2 calls and 41 seconds. The vendor also reports full-context replay used about 12x more input tokens at equal accuracy.

For builders: memories are readable, exportable, and deletable per user, and pipeline instructions steer retention.
