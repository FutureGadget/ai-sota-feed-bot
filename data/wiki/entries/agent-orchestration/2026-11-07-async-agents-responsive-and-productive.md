---
title: "Async agents must stay responsive while working: LangChain says the old loop cannot do both"
date: 2026-11-07
theme: runtime-substrate
evidence: [9c4184d44164e0d7]
---
LangChain argues (vendor post) that agents given bigger goals need two properties at once: **responsive**, acting on a new instruction immediately with the full prior context, and **productive**, advancing many large tasks concurrently. Its claim is that the single blocking agent loop most teams have used cannot deliver both, so a long task leaves the agent unreachable until it finishes.

The post frames this as an architecture change, not a prompt change: background work, mid-task steering and progress updates need a runtime that holds state outside one model call.

For builders: if users will redirect a running agent, plan for durable state, interruptible runs and status reporting before adding more parallelism.
