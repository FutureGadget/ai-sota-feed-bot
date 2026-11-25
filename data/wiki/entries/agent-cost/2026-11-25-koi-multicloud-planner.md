---
title: "Koi plans inference deployments across clouds and GPUs by learning from every run: 1.18x goodput, 20% cheaper"
date: 2026-11-25
theme: caching-and-serving
evidence: [925d484a6a3e5e81]
also: [scalability]
---
Choosing a cloud, region, and GPU type for an LLM workload often means picking a deployment nobody has run. Koi treats each run as an experiment, records why it performed as it did in a causal graph, and reuses that for the next plan. On H100, A100, and RTX PRO 6000 GPUs in three Google Cloud regions, over 25 workloads and ten models, it delivered **1.18x** the SLO-meeting goodput of OpenEvolve at **20%** lower cost per token. Without learning from new runs it lost **44%**; a tool-less, memory-less LLM planner got **71%** less goodput in simulation.

For builders: placement decisions drift as prices and fleets change. A planner that learns from its own runs beats a fixed rule.
