---
title: "Azure Container Apps Sandboxes reach GA: one microVM per workload, subsecond start, suspend/resume"
date: 2026-10-01
theme: managed-platforms
evidence: [914f78823eb69ce9]
---
Microsoft made **Azure Container Apps Sandboxes** generally available, a hardware-isolated microVM layer (one microVM per workload) provisioned from **prewarmed pools with subsecond startup** and suspend/resume of memory and disk state, aimed at agent platforms and code-execution services. Container Apps Express, which runs on it, also reached GA and scales to zero, but lacks custom domains, zone redundancy, Key Vault references, OpenTelemetry, and Dapr.

Snapshot-based idle handling replaces keeping sandboxes warm. GKE Agent Sandbox takes the same route (see [agent latency](/topic/agent-latency)).
