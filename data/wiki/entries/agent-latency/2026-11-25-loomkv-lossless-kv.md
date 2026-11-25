---
title: "LoomKV: lossless KV compression to 0.71x size gives 2.7-3.6x goodput past LMCache's eviction cliff"
date: 2026-11-25
theme: kv-state
evidence: [f1cc2271c89a756c]
---
LoomKV compresses KV cache **losslessly** with a per-head 3-bit code over BF16 high bytes, storing BF16 KV at **0.71x** raw size and FP8 at 0.85-0.87x, on an unmodified vLLM + LMCache engine. In tier mode, compressed DRAM/SSD tiers behave like **1.4x** larger raw tiers on the AgentX agent trace: **2.7-3.6x** goodput and **1.9-3.1x** lower mean TTFT across LMCache's LRU cliff. Pool mode fits **1.31-1.34x** more tokens on GPU. When capacity is not the limit, it costs at most **2.2%** throughput, and tier mode is bit-exact.

For builders: agent prefix reuse is capacity-bound. Lossless compression buys tier capacity without the output drift lossy KV quantization brings.
