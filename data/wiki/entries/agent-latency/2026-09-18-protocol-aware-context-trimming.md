---
title: "Context trimming hits a failure cliff below half the budget; protocol-aware trimming holds"
date: 2026-09-18
theme: less-work-per-step
evidence: [a3b54d5a91acaa5a]
---
A study of five trimming strategies on multi-step agentic workflows finds recency, relevance, and summarization save about 60% of tokens but drop task success to **66.6-77.3%**. Protocol-aware trimming, which keeps instructions, tool state, and unresolved dependencies, reaches 92.2%; adding adaptive budget guardrails reaches **96.0% success** and 1.0% cascading failure while still saving 56.0% of tokens.

Keeping 25% or less of context raises failure odds **10.92x** versus keeping 50% or more (p < 0.001). That is a floor under how far [compaction](/topic/context-compaction) can go before latency savings cost correctness.
