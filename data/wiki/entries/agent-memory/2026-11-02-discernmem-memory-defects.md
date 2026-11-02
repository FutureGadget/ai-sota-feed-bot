---
title: "DiscernMem repairs flawed shared memories and learns when each one should apply"
date: 2026-11-02
theme: memory-integrity
evidence: [7d1c303b6572b6ff]
---
Team-level success or failure can't tell a multi-agent system whether a stored memory is wrong or was just used in the wrong situation. **DiscernMem**, a training-free method, handles both. It compares runs with the memory, with a single memory, and with none to diagnose defective rules, and it tests each repair against earlier tasks so useful behavior isn't lost. A meta-memory records each memory's past uses and effects, so its owner role learns when to apply or skip it.

Paper-reported, on Qwen3-4B: best average score on AutoGen, CAMEL and MacNet, ahead of the strongest baseline by 0.51-4.32 points. For builders, treat memory as versioned rules with regression tests and usage records, not an append-only log.
