---
title: "Modal drops central coordination to reach 1 million concurrent sandboxes in under 60 seconds"
date: 2026-09-23
theme: coordinator-free-scheduling
evidence: [485666e1560ba32b]
---
Modal rebuilt its sandbox infrastructure after Kubernetes-style orchestration capped out: etcd can't be sharded within a keyspace, and scheduling work grows with container and node count, so **the coordinator became the bottleneck before the hardware did**.

The rebuild removes it. A horizontally scaled fleet of scheduling servers load-balances requests, each worker accepts or rejects a sandbox creation over RPC based on its own free resources, and workers publish state to one Redis stream the team expects to hold past 100,000 workers. Reported results: **1 million concurrent sandboxes in under 60 seconds**, about 50,000 creations per second, and median cold start under 0.5 seconds.
