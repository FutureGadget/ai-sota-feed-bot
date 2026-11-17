---
title: "Generic recovery advice after a tool fault cut agent success 8.3 points; a tested policy added about 10"
date: 2026-11-17
theme: calling-reliability
evidence: [b9f35f290ebb4bb0]
also: [agent-benchmarks]
---
AgentFaultBench injects tool errors into LangGraph and CrewAI agents working in an isolated GitLab and checks the final files, issues, required reads and response. Across 1,944 planned runs, recovery advice changed success by **-8.33**, 0.00 and +1.06 points against a neutral reminder.

A revised recovery policy, tested on six unseen tasks, reached **161/192** correct final states versus 142/192 with neutral feedback, a gain of about **+10 points**. GPT-4o mini improved; Claude and Sol already completed the recoverable cases. No human validation was collected.

For builders: error messages and recovery hints are prompt changes that can hurt. Test them against a neutral-feedback control and verify end state, not the agent's report.
