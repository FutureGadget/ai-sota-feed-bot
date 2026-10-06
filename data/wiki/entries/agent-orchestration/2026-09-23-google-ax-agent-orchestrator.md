---
title: "Google open-sources AX, a Kubernetes-style orchestrator that runs agents as stateful actors"
date: 2026-09-23
theme: runtime-substrate
evidence: [0c87e9548be43d83]
also: [multi-agent]
---
Google's **AX** runs autonomous agent workloads on a runtime, Agent Substrate, that treats **each agent as a stateful actor** rather than a stateless request handler. It suspends and resumes tasks to save resources and cut latency during idle phases, under a control plane with Kubernetes-style primitives for tasks and resources.

Scheduling and lifecycle management for agents arrives as a platform a team could adopt wholesale, instead of assembling it from queues and leases.
