---
title: "Evolving the safety harness against evolving attacks cut injection success from 50% to 3%"
date: 2026-11-18
theme: harness-controls
evidence: [7a0c85ad18799951]
---
**Evolution Under Fire** searches over complete, executable safety harnesses, keeping the model, tools and evaluator fixed. It then evolves attacks that keep the task working to stress the winner, and evolves the harness again. On AgentDyn with GPT-4o-mini, attack success fell from **50.4% to 3.0%**, with clean and attacked utility both improving. On Agent-SafetyBench with Qwen2.5-7B it fell only from 82.6% to 62.0%. An evolved harness moved to Qwen3.5-35B-A3B without retuning dropped attacks from 32.1% to 0.9%.

For builders, the harness, not only the model, is the thing to optimize. The large gap between the two benchmarks shows that a harness tuned on one benchmark needs its own adversarial evaluation before you rely on it.
