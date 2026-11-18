---
title: "A serving system that retunes itself online to agent traffic beat Dynamo on end-to-end latency"
date: 2026-11-18
theme: agent-traffic
evidence: [d87fc1f9790063c0]
---
**Evolving Infra** (MIT Han Lab with Georgia Tech, UIUC, Berkeley, NVIDIA and OpenAI authors) is an LLM serving system that adapts to the agent workload purely online, with no offline profiling. The authors served coding, math and computer-use agents on GLM-5.2 and Kimi K2.6 across up to 256 GB300 GPUs. They report up to **4.1× lower mean end-to-end latency** and **14× lower P95 time to first token** than NVIDIA Dynamo. These are author-reported figures.

The claim worth testing is that agent traffic shifts too much for a configuration profiled once. If it holds, serving teams would tune continuously against live agent sessions instead of benchmarking a fixed recipe at deploy time. The repo ships agent traces on Hugging Face for replay.
