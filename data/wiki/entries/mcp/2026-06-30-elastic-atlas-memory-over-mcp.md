---
title: "Elastic's Atlas serves agent memory over MCP with per-user isolation"
date: 2026-06-30
theme: beyond-tools
evidence: [ca2de3ecb9f0eb55]
---
Elastic open-sourced **Atlas**, an Elasticsearch-based system that keeps three categories of memory for agents, integrates through MCP, and isolates memories per user. It scored **0.89 Recall@10** on question answering (vendor-reported).

Agent memory becomes another MCP server, so any MCP client can share the same memory store.
