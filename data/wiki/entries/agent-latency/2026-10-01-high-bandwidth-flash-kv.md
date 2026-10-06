---
title: "High-bandwidth flash could hold agentic KV state, but write endurance limits it"
date: 2026-10-01
theme: kv-state
evidence: [0588c8c0813b65e1]
---
A characterization study evaluates **high-bandwidth flash (HBF)** as extra accelerator memory for LLM serving. Agentic workloads make retaining KV state for reuse more important because they repeat interactions over growing contexts.

HBF adds capacity, but its access costs and **limited write endurance** complicate its use for state that is rewritten every step. It is a hardware option to watch, not one to plan around yet.
