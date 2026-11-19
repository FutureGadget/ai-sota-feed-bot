---
title: "An LLM router swapped for an intent classifier was rolled back in 23 minutes: the call did more than routing"
date: 2026-11-19
theme: regressions-and-reverts
evidence: [ce41be6f266f183c]
also: [agent-reliability]
---
Audiala swapped an LLM router for a dedicated decision model and reverted **23 minutes** later. The new model classified intent fine, but the old LLM call was also resolving cities, conversational references and tool-control flags. The team had evaluated one responsibility and replaced several.

The same survey of decision-model adoption found related failures: candidate construction constrained action selection, missing handoff instructions weakened downstream agents, and faster decisions sometimes created more recovery work. For builders: before replacing a prompt with a cheaper component, inventory every field downstream code reads from its output and test each one.
