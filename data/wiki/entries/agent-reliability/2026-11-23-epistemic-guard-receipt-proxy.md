---
title: "An out-of-process MCP proxy checks agent prose against signed tool receipts on CPU"
date: 2026-11-23
theme: hallucination-containment
evidence: [3ff306b207bee77b]
also: [agent-memory, mcp]
---
epistemic-guard sits between the agent and its MCP servers as a stdio proxy, signs tool receipts with keys held outside the agent process, and appends them to a Merkle log. After each turn, small INT8 encoders on CPU check whether the agent's prose claims actions the receipts do not show. Memory writes are gated by provenance, and syndicated mirrors of one page count as one source.

On a frozen 250-item set it scores **93.2%** at 17.9 ms median CPU latency, above 12-14B GPU judges by about 6.5 points. On 60 live traces it caught 96% of hazards, but with a **38%** false-positive rate. For builders: "the tool succeeded" is checkable against a receipt; the detector is still noisy.
