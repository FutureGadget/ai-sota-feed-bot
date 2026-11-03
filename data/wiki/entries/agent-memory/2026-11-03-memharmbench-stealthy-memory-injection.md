---
title: "Injected memories steer later sessions while tasks still finish normally"
date: 2026-11-03
theme: memory-integrity
evidence: [1c851e04a1a59b28]
also: [prompt-injection]
---
MemHarmBench exposes an agent to malicious instructions, checks whether memory retained them, deletes the attack content, then starts a fresh session with a legitimate task. It scores whether the agent follows the attacker's intent, completes the task, and shows execution anomalies, across users, project owners and external stakeholders as victims.

Cross-session attacks stayed behaviorally stealthy. Agents often finished tasks normally with no detectable anomaly while still making decisions aligned with the attacker. Task success is therefore not a safety signal for persistent memory. Audit what memory writes retain and where they came from.
