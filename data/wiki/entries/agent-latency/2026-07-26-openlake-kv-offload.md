---
title: "OpenLake offloads KV cache to shared RAM/NVMe, cutting cross-host TTFT from 44s to 0.6s"
date: 2026-07-26
theme: kv-state
evidence: [309c04c4364dddf7]
---
OpenLake offloads KV state from GPU memory into a **shared RAM and NVMe tier**, with a CUDA kernel that losslessly compresses blocks before they leave the GPU. Its motivation: one 256K-token conversation on Gemma 4 31B produces about 43GB of KV state, more than half an 80GB H100.

Because the tier is shared, a prefix cached on one host is cheap to fetch from another instead of being recomputed. On a 128K-context workload, **time-to-first-token fell from 44 seconds to 0.6** when the prefix was reused across hosts. The project claims 50% lower long-horizon inference cost.
