---
title: "vLLM tuned for SemiAnalysis AgentX reaches 130K tokens per GPU-second on agentic traffic"
date: 2026-09-10
theme: agent-traffic
evidence: [9bd5188163ee117b]
---
vLLM's account of optimizing for **SemiAnalysis AgentX**, a benchmark that scores serving stacks on agentic rather than chat-shaped traffic, combines KV-cache management, parallelism, scheduling, and prefill/decode disaggregation into one tuned stack. It reaches **up to 130K tokens per GPU-second** and reports a 14.6x-106x serving-cost advantage over Opus 5 on the benchmark.

It is less a new lever than evidence that the existing levers compound when tuned together for agent traffic. The cost comparison is vLLM's own.
