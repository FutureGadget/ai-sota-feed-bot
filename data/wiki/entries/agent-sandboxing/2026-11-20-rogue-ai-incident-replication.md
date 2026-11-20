---
title: "Replicated agent incidents show most harm comes from missed ordinary hazards, not attackers"
date: 2026-11-20
theme: guardrails-and-verification
evidence: [2c7619273522d7ac]
also: [agent-reliability, prompt-injection]
---
ROGUE-AI rebuilds reported agent incidents offline, each with a control that removes only the blamed cause. It reproduced the harm in **89% of 108 replications**. GPT, Claude, Gemini, and DeepSeek agents repeated the mistake in 18-33% of runs, against at most 1% without the cause.

Of 72 incidents with real harm, **62 had no attacker**: the agent did its task and missed an ordinary hazard, such as a database shared with the live site. These caused more harm than injection replications, which injection defenses cannot catch. A warning after each tool output naming the hazard cut harm for all five models; a same-length generic note did not. For builders: label hazards in tool output, and rerun replicated incidents before each release.
