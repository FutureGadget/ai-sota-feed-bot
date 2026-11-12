---
title: "One agent serving every user beat one agent per user in all four shared-resource environments"
date: 2026-11-12
theme: when-it-pays
evidence: [23e8ac3f97dad8c1]
---
Anthropic Fellows tested teams where each user delegates to their own agent over a shared resource: a token budget, a clinic calendar, a group order, a merge queue. A single coordinator beat the peer-to-peer team in all four, by about 10 to 45 points for Claude Opus 5 and Sonnet 5.

- **Stalling:** from 4 to 16 agents, the share that ever acted fell from 66% to 10% (Sonnet 5).
- **Race:** a user's constraint reached the ordering agent in 94-99% of episodes but was in its context at commit in only 47-67%.

Fixes were environment-specific. A team lead closed the budget gap; a platform guard that blocks checkout until pending messages are read recovered 62-73% of failed orders. Simulated users; lab-reported. Three environments ship as MAMUBench.
