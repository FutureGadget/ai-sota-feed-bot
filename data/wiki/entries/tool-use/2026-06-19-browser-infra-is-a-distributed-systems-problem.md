---
title: "Hosting browsers for agents is a distributed-systems problem, not a model problem"
date: 2026-06-19
theme: production-runtimes
evidence: [5b5273180a38e7c0]
---
Paul Klein's talk on cloud-hosted browser infrastructure for agents covers **bursty, stateful multi-tenancy** and securing Chromium against remote code execution with Firecracker microVMs. MCP is the layer that turns complex websites into tools an agent can call.

The model's tool-calling skill does nothing for these failures. Capacity, isolation, and sandbox escape are ordinary infra work that the tool layer inherits.
