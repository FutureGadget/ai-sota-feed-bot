---
title: "Agentest runs 165 deterministic checks over recorded OpenTelemetry agent traces with no LLM judge"
date: 2026-11-19
theme: reading-traces
evidence: [07a109e2a65bebbe]
also: [agent-evaluation, agent-tracing]
---
Agentest reads the OpenTelemetry GenAI traces an agent already emits (plus A2A and MCP) and runs **165 offline tests** on what the agent did: claimed success it did not earn, acting before verifying, following a hidden instruction, calling a forbidden tool, or leaking personal data. It needs no API key, network or LLM judge, so the same trace always yields the same verdict, and it runs in CI.

For builders: if you already export OTel GenAI spans, trace-level assertions are a cheap regression gate that sits beside judge-based evals rather than replacing them.
