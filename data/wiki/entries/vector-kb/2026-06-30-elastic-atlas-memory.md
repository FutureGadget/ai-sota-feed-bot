---
title: "Elastic's open-source Atlas builds tiered agent memory on Elasticsearch, served over MCP"
date: 2026-06-30
theme: datastores-you-run
evidence: [ca2de3ecb9f0eb55]
---
Elastic open-sourced **Atlas**, which keeps three categories of agent memory on Elasticsearch, isolates memories per user, and connects to agents over [MCP](/topic/mcp). It scored **0.89 Recall@10** on its question-answering evaluation.

The retrieval store is the search cluster a team already runs, not a new dependency, and per-user isolation comes from the platform rather than application code.
