---
title: "Deep Agents turns on prompt caching by default for up to ~80% lower token cost"
date: 2026-06-27
theme: caching-and-filtering
evidence: [edd85739d7d91365]
also: [agent-cost]
---
LangChain's Deep Agents uses provider prompt caching to cut LLM token costs by **up to 80% across every major provider, with no extra config**.

An agent loop re-sends a large, stable prefix every turn: system prompt, tool schemas, prior steps. That is exactly the input a provider prompt cache discounts. Caching the stable prefix becomes a default the framework owns, not a knob each team has to discover.
