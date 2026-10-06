---
title: "LangChain mines trace failures to fine-tune judges cheaper than frontier models"
date: 2026-07-07
theme: cheaper-models
evidence: [4a0a79e7203bae64]
---
LangChain describes improving agents as **data mining**: cluster failures out of production traces, fine-tune judge models on them that run cheaper than frontier LLMs, then hill-climb the agent against those evals.

It is the cheap-instrumentation-over-model-swap move applied to evaluation. The judge's cost scales with every trace, so it is the first place a downshift pays back.
