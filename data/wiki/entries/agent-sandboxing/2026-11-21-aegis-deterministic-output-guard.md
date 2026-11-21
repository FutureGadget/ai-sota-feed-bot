---
title: "Aletheia Aegis puts a deterministic CPU output guard before any LLM judge"
date: 2026-11-21
theme: guardrails-and-verification
evidence: [a80f0b7fcfaf73bb]
also: [llm-as-judge]
---
Aegis inspects every agent output before it reaches a user. A deterministic first stage runs on CPU in a vendor-reported **0.019-0.029 ms at p95** and hard-blocks credential leaks and life-safety failures, **failing closed** and skipping the upstream judge entirely. An optional semantic judge handles only the cases patterns cannot settle. It runs offline and retains no response text.

The design bet is that running a second LLM on 100% of outbound traffic fails at scale on cost, latency, and as an exfiltration path. For builders: enforce non-negotiable output invariants with deterministic code, and spend judge calls only on the ambiguous remainder.
