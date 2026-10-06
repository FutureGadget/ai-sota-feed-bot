---
title: "AWS Dogwood extends Cedar so policies can reason about an agent's sequence of tool calls"
date: 2026-08-17
theme: agent-authorization
evidence: [410ca031ddd240de]
---
AWS open-sourced Dogwood, a policy language that extends Cedar with **temporal conditions**, so a rule can depend on an agent's prior tool calls rather than one request in isolation. It covers approvals, rate limits, and running totals, ships under Apache 2.0, and is supported in AgentCore Policy. The reference interpreter is not production-ready.

Per-call scopes can't express a rule that depends on what the agent already did in the session. Sequence-aware policy can, and multi-step exfiltration chains are exactly that shape.
