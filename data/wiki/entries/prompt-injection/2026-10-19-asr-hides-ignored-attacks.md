---
title: "Low attack success rates mostly mean agents ignored the injection, not that they resisted it"
date: 2026-10-19
theme: eval-escapes
evidence: [ee884278a0d18afe]
---
A paper audited 33,000 trajectories from eleven open-weight agents (2-14B parameters) on InjecAgent and AgentDojo. Attack success rate (ASR) counts every failed attack as a defense, but a label-blind LLM judge found most failures were **ignored** (76-80%) rather than **refused** (17-18%).

With identical weights, changing only the system prompt moved InjecAgent ASR from 0.2% to 43%. In 21.7% of AgentDojo episodes the agent stayed safe but did not finish the user's task (all paper-reported).

For builders: a low ASR from a vendor benchmark is weak evidence. Ask for how attacks failed and whether the user task completed, and re-test after any prompt change.
