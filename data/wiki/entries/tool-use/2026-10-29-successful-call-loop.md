---
title: "A successful tool call is not progress: an agent reran one SQL query 254 times"
date: 2026-10-29
theme: calling-reliability
evidence: [e79cc677e615b2d8]
also: [agent-cost]
---
Funnel A/B-tested GLM-5.2 against Claude Opus 4.8 on its internal data agent (self-reported). GLM answered each model call faster (7.8s vs 18.1s) but made 66% more tool calls (19 vs 11) and finished tasks 14% slower end to end. Twice it reran the same successful query 113 and 254 times, because the tool returned only a 20-row preview and the model never recognized the limit.

Funnel traced it to the harness: ambiguous tool contracts, saved instructions naming tables that did not exist, and no repeated-call guard. For builders: label previews versus complete results, detect repeated equivalent calls, and cap execution budgets before swapping models.
