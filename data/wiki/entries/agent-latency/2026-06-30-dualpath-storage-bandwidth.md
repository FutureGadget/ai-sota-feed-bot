---
title: "DualPath: agentic inference is bound by storage bandwidth, not compute"
date: 2026-06-30
theme: kv-state
evidence: [e313a171aa375adf]
---
DualPath finds that the binding constraint in agentic LLM inference is **storage bandwidth**, not compute: the agent's growing KV and context state has to be streamed back in at every step of the loop.

That changes the optimization target. Faster kernels help less than shrinking, offloading, sharding, or reusing the state each step has to move.
