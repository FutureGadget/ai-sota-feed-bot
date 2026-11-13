---
title: "The best agent resolves 69.6% of single tool requests but only 39.8% of three-turn dialogues"
date: 2026-11-13
theme: calling-reliability
evidence: [7f9cd8c3ff5fb56c]
also: [agent-benchmarks]
---
ToolTurns has 2,620 problems over 1,827 tools and 11,004 API endpoints. Each dialogue opens with a deliberately underspecified request and adds two context-dependent follow-ups, so the agent must clarify, call tools, and retain earlier turns. A simulated user reveals withheld context.

- **Compounding:** across nine models, the best resolves 69.6% of individual requests and completes 39.8% of full dialogues.
- **Follow-ups are harder:** every model scores lower on follow-up requests than on the first.
- **Rubrics mislead:** dialogue-quality rubric scores and task success can rank models very differently.

Single-request tool benchmarks overstate conversational agents. Score whole dialogues, and do not use a conversation-quality rubric as a proxy for task success. Paper-reported; the user simulator is open source.
