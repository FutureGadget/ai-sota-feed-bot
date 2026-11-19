---
title: "An RL LoRA for Qwen3.8-27B matches max-effort thinking with thinking off at about 4.5x fewer tokens"
date: 2026-11-19
theme: cheaper-models
evidence: [dbede62d4d711d8c]
also: [agent-orchestration]
---
A LoRA adapter trained with reinforcement learning as the model behind the **pi** coding agent matches the base Qwen3.8-27B at its highest reasoning effort while running with thinking off: **64.7% vs 64.7%** on SWE-bench Pro and **56.6% vs 54.2%** on Terminal-Bench 2.1, generating about **4.5x fewer tokens** per task. Turning thinking on for the adapter adds nothing. Results are author-reported, one attempt, under the pi harness only.

For builders: tuning an open model to one harness can buy the reasoning budget back as token savings, but the gain is harness-specific and needs re-validation if you swap the scaffold.
