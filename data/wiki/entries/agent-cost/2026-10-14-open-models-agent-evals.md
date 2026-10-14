---
title: "LangChain's early evals put GLM-5 within 4 points of Opus 4.6 at roughly a fifth of the price"
date: 2026-10-14
theme: cheaper-models
evidence: [40a221f953410175]
---
LangChain ran 138 Deep Agents test cases per model and reports **vendor-reported, early** results. Correctness: Opus 4.6 0.68, Gemini 3.1 Pro 0.65, GLM-5 0.64, GPT-5.4 0.61, MiniMax M2.7 0.57.

- Output pricing per million tokens: GLM-5 $3.15 vs Opus 4.6 $25.
- LangChain's estimate for 10M output tokens a day: about $250 on Opus vs about $12 on MiniMax M2.7.
- Open models trail on memory and conversation; categories hold only a handful of cases each.

Each model ran at its provider's default thinking level, and the open models ran on different hosts. Rerun the eval on your own task mix before downshifting.
