---
title: "Packing ASR requests with CUDA MPS cut Heidi Health's GPU count 75%"
date: 2026-08-28
theme: caching-and-serving
evidence: [5b17581a4141c149]
---
Heidi Health found each ASR inference request used only **15-20% of an NVIDIA L40S's streaming multiprocessors**. Packing 4-8 concurrent requests per GPU with CUDA's Multi-Process Service and Triton, instead of one GPU per request, cut the GPUs needed for the same throughput by **75%, from 16 instances to 4**.

Utilization, not list price, often sets the self-hosted bill. Measure how much of each GPU a request uses before buying more.
