---
title: "Google Workspace charges per MCP call while REST apps keep a large free allowance"
date: 2026-11-28
theme: servers-in-production
evidence: [b0c1591ccb1ee91c]
also: [agent-cost]
---
Martin Alderson reads Google's new Workspace terms as the first major product to price agent access separately. Agents must use MCP rather than the REST API. MCP calls cost about **$0.20 per 1,000** email reads, with **5,000 free calls a day** shared across a whole Google Cloud project.

A REST app on the paid tier still reads **10 million emails a day** free before it pays, and each REST user gets their own per-minute quota. The author estimates a user making 10,000 MCP requests a month costs the AI vendor about $2. How Google will tell agents from apps is unclear.

For builders: budget per-call charges for every agent that touches Workspace data. Expect other systems of record to try the same pricing.
