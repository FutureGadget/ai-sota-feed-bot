---
title: "Trimming agent history without preserving its protocol can break the agent"
date: 2026-09-18
theme: harness-and-context
evidence: [a3b54d5a91acaa5a]
---
"Protocol-Preserving Context Trimming for Agentic Workflows" studies agents whose histories hold instructions, tool states, intermediate decisions, and unresolved dependencies. Unrestricted growth drives up compute, but trimming that ignores the **interaction protocol can break the agent**, not just make it less accurate.

Its budget guardrails keep trimming inside the protocol's constraints, not only inside a token count. It complements ACM's cost/fidelity framing with an account of *how* trimming fails.
