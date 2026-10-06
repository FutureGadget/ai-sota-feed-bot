---
title: "AWS's multi-turn RL checklist: trusted environment, external eval, task-aligned reward"
date: 2026-07-04
theme: learned-planning
evidence: [bfeae69131afd34f]
---
AWS's best practices for multi-turn RL in SageMaker AI list the operational steps for training agents on long interactions:

- build a training environment you can trust
- run an **external evaluation** separate from the reward signal
- design the **reward to match the end task**
- manage what changes once the agent runs for multiple turns
- monitor the metrics that tell you when to iterate

It is the checklist underneath "just fine-tune on tool interactions".
