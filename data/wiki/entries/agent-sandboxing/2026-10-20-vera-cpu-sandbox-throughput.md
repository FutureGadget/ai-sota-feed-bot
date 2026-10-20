---
title: "Modal reports NVIDIA Vera CPUs about double sandbox throughput under heavy concurrent load"
date: 2026-10-20
theme: managed-platforms
evidence: [2ccafb2a756f8408]
---
Modal benchmarked NVIDIA's Arm-based Vera CPU on **Agentless Agent Bench**: 50 Terminal-Bench oracle solutions with network calls removed, run in concurrent containers. On a quiet host, serial latency was only marginally better than x86 and Graviton alternatives. Under 50 to 150 concurrent containers, Vera completed roughly twice the tasks in a fixed window without worse latency (vendor-reported; Modal has not shipped Arm support yet).

The context is sandbox workloads: idle while waiting on an LLM, then CPU spikes 10x above baseline on an `npm install`, which makes burst absorption and noisy neighbors the cost driver.

For builders: benchmark sandbox hosts under concurrency, not single-task latency.
