---
title: "AgentCore Memory adds structured metadata filtering for multi-tenant recall"
date: 2026-07-03
theme: datastores-you-run
evidence: [9283a6f418d96ab7]
---
AWS's AgentCore Memory now carries **metadata across configuration, ingestion, and retrieval**, so recall can be narrowed by fields such as tenant, document type, or time range before similarity ranking. AWS frames it for multi-agent and multi-tenant architectures.

Metadata filters are the practical complement to hybrid retrieval: they enforce tenant boundaries and cut the candidate set deterministically instead of trusting embedding distance to keep tenants apart.
