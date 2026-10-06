---
title: "Harbor pairs LangSmith sandboxes and observability with Deep Agents to evaluate long-running agents"
date: 2026-07-03
theme: eval-in-production
evidence: [1bfbb319ced0695a]
---
LangChain plugged Deep Agents, LangSmith sandboxes, and observability into **Harbor** as one runner for **long-running, stateful agents**.

Stateful agents need an environment that persists across steps and can be inspected afterward. A plain dataset-and-scorer loop cannot evaluate them.
