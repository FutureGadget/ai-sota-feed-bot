---
title: "RL-learned batching policies target bursty traffic that static batching can't follow"
date: 2026-07-07
theme: agent-traffic
evidence: [c841afae435d6473]
---
Static batching policies need manual tuning per traffic shape and cannot adapt when patterns shift. This paper trains **REINFORCE and PPO agents** to learn batching and routing policies, modeling queue state, request type, and GPU availability on a discrete-event simulator validated against queuing theory and production traces (Azure Functions, BurstGPT).

Agent tool-calling produces exactly this bursty, heterogeneous load, not the steady arrival rate a chat workload has.
