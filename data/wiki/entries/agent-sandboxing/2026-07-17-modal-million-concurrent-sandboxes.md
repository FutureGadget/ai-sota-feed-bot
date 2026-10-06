---
title: "Modal's scheduler launches up to 1 million concurrent sandboxes per workspace in seconds"
date: 2026-07-17
theme: managed-platforms
evidence: [764c073dd4e1fc67]
---
Modal describes how it built a scheduler that scales to **1 million concurrent sandboxes per workspace within seconds**.

Once an org runs many agents (or RL rollouts) at once, scheduler throughput and cold-start latency matter as much as the isolation boundary itself. Sandbox choice becomes a capacity question too.
