---
title: "Crafted inputs can trap an LLM guardrail in long reasoning loops, denying service to the agent"
date: 2026-06-19
theme: guardrails-and-verification
evidence: [6b3ed4b86d0301bf]
---
"From Shield to Target" shows the reasoning that makes LLM guardrails effective against injection is itself an attack surface. A beam-search framework crafts natural-language payloads that **maximize the guardrail's reasoning length**, trapping it in extended loops and producing a systematic denial-of-service against the protected agent.

A guardrail model adds per-call cost and a new failure mode. Budget its latency and fail closed when it times out.
