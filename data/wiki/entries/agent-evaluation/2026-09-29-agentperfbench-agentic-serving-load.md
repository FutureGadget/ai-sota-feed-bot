---
title: "AgentPerfBench shows chatbot-style serving benchmarks understate agentic load"
date: 2026-09-29
theme: domain-benchmarks
evidence: [8424df2cc3f5d4ac]
---
**AgentPerfBench** replays multi-turn traces from SWE-Bench and TerminalBench against serving engines such as vLLM and SGLang. Existing inference benchmarks **miss realistic context-length growth** and are not run at hardware saturation, so single-turn chatbot workloads understate agentic load.

Capacity plans built on chatbot benchmarks will be wrong for agents. See [agent latency](/topic/agent-latency).
