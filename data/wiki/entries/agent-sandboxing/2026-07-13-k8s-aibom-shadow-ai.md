---
title: "Google open-sources k8s-aibom to inventory unregistered AI workloads on GKE"
date: 2026-07-13
theme: guardrails-and-verification
evidence: [f7912534a54859ea]
---
**k8s-aibom** is a lightweight, **unprivileged** Kubernetes controller that watches the cluster API and container environments, detects running AI runtimes such as vLLM and Triton, and generates standard CycloneDX AI bills of materials.

It targets shadow AI: workloads deployed without registration that evade scanners because teams won't accept privileged DaemonSets or pod-spec edits. You cannot sandbox or scope what you don't know is running.
