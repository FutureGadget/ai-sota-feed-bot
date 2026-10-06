---
title: "Continuous batching on an iPhone nearly doubles multi-agent throughput versus llama.cpp"
date: 2026-08-28
theme: agent-traffic
evidence: [ec2a07215adc6507]
---
A from-scratch Swift port of vLLM's **continuous batching** onto an iPhone's MLX kernels left-pads late-arriving requests and merges them into a shared KV-cache offset. It hit **169 aggregate tokens/sec across 8 concurrent streams** versus llama.cpp's 90.

A 16-request, ~17K-prompt-token multi-agent workload ran in 25 seconds without thermal throttling; llama.cpp needed 47 seconds for half the load. Continuous batching answers concurrent decode on-device too, not only in the data center.
