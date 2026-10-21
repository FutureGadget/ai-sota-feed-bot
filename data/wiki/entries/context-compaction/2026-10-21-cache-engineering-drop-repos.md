---
title: "Dropping KV cache segments beats summarizing history, without re-prefilling the kept context"
date: 2026-10-21
theme: curating-the-working-set
evidence: [dee08d9f3dc2ded7]
also: [agent-latency, agent-cost]
---
Summarizing or trimming history rewrites the trajectory prefix, which invalidates cached states and forces a re-prefill of everything kept. "Cache engineering" instead lets the agent act on the KV cache directly: `drop` excludes chosen segments from future attention, and `repos` re-adjusts the retained keys' position encodings.

Paper-reported results for a tool-response rolling-drop policy versus threshold-triggered summarization:
- Benchmark score up 1.7 points, cost down 27.7%.
- With the AKV serving engine: up to 1.2x output throughput, 1.5x faster P95 latency.

Catch: identical token sequences can yield different cache states, so plain prefix matching is no longer a safe reuse key.
