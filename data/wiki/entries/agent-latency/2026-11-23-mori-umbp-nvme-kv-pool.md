---
title: "AMD's MoRI UMBP served the agentic KV pool from NVMe within 1% of DRAM throughput at equal size"
date: 2026-11-23
theme: kv-state
evidence: [fa08bb9c21c2e185]
also: [agent-cost]
---
The vLLM blog replayed real Claude Code sessions (median turn **142K** input tokens, over 96% already-seen prefix) on 16 MI355X GPUs running Kimi-K3. Each 1% of KV hit rate was worth about 10% throughput. Moving the 1.8 TB KV pool from DRAM to local NVMe, with an 80 GB DRAM staging buffer, kept throughput within **1%** and median TTFT within 0.8 s.

The gain is retention: a 4.6 TB NVMe pool held a **93%** hit rate at 70 sessions versus 52% for a 1.0 TB DRAM pool. The cost is drive wear, about 5.5 months of rated life at 96 sessions. Most results are single runs. For builders: size the KV tier by retention minutes, not by RAM.
