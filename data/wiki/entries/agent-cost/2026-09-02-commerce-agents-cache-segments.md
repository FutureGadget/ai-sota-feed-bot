---
title: "Three-segment prompt layout yields 90-99% cache hit rates in production commerce agents"
date: 2026-09-02
theme: caching-and-serving
evidence: [40944f4dff2445be]
---
Anthropic's commerce-agents guide reports **90-99% prompt-cache hit rates** in production by keeping a byte-identical prefix across three segments: global (rarely changes), session (stable for the conversation), and volatile (changes each turn). Only the volatile segment breaks the cache, and cached tokens read 1.5-2x faster.

Its latency levers are fewer turns, faster tools (dispatching a tool call as its arguments stream), and model choice by eval sweeps over real traffic. Spend-relevant actions stay off the model's say-so: staged, human-approved, with server-issued IDs and transaction caps.
