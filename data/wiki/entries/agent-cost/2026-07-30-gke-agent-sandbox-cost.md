---
title: "GKE Agent Sandbox reports ~75% lower cost per agent for bursty workloads"
date: 2026-07-30
theme: caching-and-serving
evidence: [7f18e7dd55749326]
---
Google reports that **GKE Agent Sandbox** cuts cost per agent by **roughly 75%** for platform teams running many agents. Agents work in bursts, so one VM per agent (the simple OpenClaw- or Hermes-on-a-VM setup) pays for idle time between bursts.

The sandboxing choice is a cost lever, not only a security control: how agents are packed onto infrastructure sets the per-agent bill. See [sandboxing](/topic/agent-sandboxing).
