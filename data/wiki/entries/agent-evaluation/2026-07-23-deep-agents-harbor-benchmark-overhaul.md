---
title: "LangChain's Harbor eval spans coding, conversation, and retrieval and gates what ships"
date: 2026-07-23
theme: eval-in-production
evidence: [35c0257d1b804bbd]
---
LangChain revamped how it benchmarks Deep Agents: one **Harbor** eval setup across **coding, conversation, and retrieval**, used to decide which changes ship rather than reporting a score afterward.

A single cross-capability gate catches a change that helps one task type while regressing another.
