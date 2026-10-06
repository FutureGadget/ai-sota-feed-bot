---
title: "A harness-to-engine protocol cuts agent time-to-first-token 2.23x by sharing workflow intent"
date: 2026-10-06
theme: agent-traffic
evidence: [3ef8a9b8fee4fad6]
---
**HEAR** is a bidirectional protocol: the agent harness sends workflow intent (dependencies, context lifecycle, objectives) and the inference engine returns live state (queues, KV-cache, resource pressure, capabilities). Policy stays separate from protocol semantics.

Under memory-constrained concurrent serving, cache-aware coordination gave a **1.61x** batch speedup and **2.23x** lower median time-to-first-token on SCBench. Workload-specific execution modes gave **1.23x** (BrowseComp-Plus) and **2.45x** (DeepResearchBench) end-to-end speedups. These are paper-reported benchmark results.

For builders: the harness knows what will be reused; engines cannot infer it from request streams alone.
