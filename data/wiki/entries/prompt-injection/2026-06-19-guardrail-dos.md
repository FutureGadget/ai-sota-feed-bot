---
title: "Crafted inputs can trap LLM guardrails in long reasoning loops, turning them into a DoS vector"
date: 2026-06-19
theme: model-defenses
evidence: [6b3ed4b86d0301bf]
---
"From Shield to Target" shows that the reasoning and task-following that make LLM guardrails effective against injection also make them a target. Attackers inject crafted data that traps the guardrail in **extended reasoning loops**, a systematic denial of service against the agent it protects.

A guardrail model is another model in the request path. Budget its latency and tokens, set timeouts, and decide in advance whether a stuck guardrail fails open or closed.
