---
title: "AWS Lambda runs GPU inference with up to 48 concurrent invocations sharing one model copy"
date: 2026-11-22
theme: concurrent-serving
evidence: [9e6bd2a43844cbfa]
also: [agent-latency]
---
Lambda Managed Instances now run event functions on EC2 G-series GPUs (G4dn through G6e) from a container image. **Concurrent invocations share a single copy of the model in GPU memory, up to 48 per execution environment**, and scaling follows GPU utilization, CPU utilization, and concurrency. Publishing a version downloads weights and warms the engine before the first event, which removes per-request cold starts. AWS ships vLLM and SGLang base images that need no handler code; a model swap is a config change.

Pricing is the EC2 On-Demand rate plus a 9.75% management fee and $0.20 per million requests. For builders: event-driven agent side tasks can get GPU inference without a cluster, at a premium over running the instances yourself.
