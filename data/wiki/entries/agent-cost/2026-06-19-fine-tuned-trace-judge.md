---
title: "A fine-tuned open judge matches frontier trace-judging at ~1/100th the cost"
date: 2026-06-19
theme: cheaper-models
evidence: [4235792e910ea51a]
also: [cost-controls, proving-agent-roi]
---
LangChain and Fireworks fine-tuned an open model to mine perceived-error signals from production traces, **matching frontier-judge performance at roughly 1/100th the cost**.

Evaluation is a cost line item too. A frontier judge over every trace is often unaffordable; a small judge trained on your own traces makes continuous judging part of the budget instead of a reason to sample. See [LLM-as-judge](/topic/llm-as-judge).
