---
title: "AWS Dogwood extends Cedar so policies can reason over an agent's prior tool calls"
date: 2026-08-17
theme: permission-policy
evidence: [410ca031ddd240de]
---
AWS open-sourced **Dogwood** (Apache 2.0), a policy language that adds **temporal conditions** to Cedar. Rules can condition on an agent's earlier tool calls, covering approvals, rate limits, and running totals across a session rather than one request at a time. AgentCore Policy supports it; AWS says the reference interpreter is **not production-ready**.

Per-call checks miss harm spread across many individually allowed calls; sequence-aware rules can cap the running total.
