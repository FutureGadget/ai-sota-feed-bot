---
title: "OpenLake offloads KV cache to shared RAM/NVMe, cutting long-context GPU cost 48%"
date: 2026-07-26
theme: caching-and-serving
evidence: [309c04c4364dddf7]
---
OpenLake is an open-source storage engine that moves LLM KV caches **from GPU memory into a shared RAM/NVMe tier**, compressing blocks losslessly before they leave the GPU. A prefix cached on one host is cheap to fetch from another instead of being recomputed.

On a 128K-context workload, total GPU time fell from **1,169 to 606 seconds, a 48.2% GPU-cost reduction**. As agent contexts outgrow GPU memory, KV-cache offload becomes its own storage-engineering problem.
