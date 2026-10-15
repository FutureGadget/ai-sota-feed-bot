---
title: "BigQuery caps generative AI SQL functions with four daily token quotas"
date: 2026-10-15
theme: vendor-spend-controls
evidence: [2921d496df7e8c9c]
also: [agent-cost]
---
Google Cloud made token-based cost management generally available for BigQuery's LLM functions (`AI.GENERATE`, `AI.CLASSIFY`, `AI.IF`, `AI.SCORE`, `AI.AGG`). Four daily quotas run through IAM: input and output tokens, each per project and per user.

- Defaults: 200B input and 20B output tokens per project; 150B and 15B per user.
- Quotas are global across regions, and output quotas count thinking tokens.
- Lowering a quota applies immediately; raising one is a request, often auto-approved.
- Embedding functions are exempt.

For builders: the cap sits at the platform layer, so one runaway query cannot spend past it.
