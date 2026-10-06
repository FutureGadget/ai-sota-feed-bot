---
title: "Tarit is a self-hostable rust-vmm hypervisor for agent and RL sandboxes"
date: 2026-07-08
theme: managed-platforms
evidence: [9052589c403a3302]
---
**Tarit** is an open-source hypervisor built on rust-vmm for AI-agent and RL environments, pitched as a Firecracker replacement. Its authors say Firecracker, built for serverless, lacks primitives like **live snapshots without pausing the VM**. A basic orchestrator handles microVM placement, HA clusters, a warm VM pool, networking, and monitoring.

Teams that want microVM isolation without a managed sandbox vendor get a self-hosted option.
