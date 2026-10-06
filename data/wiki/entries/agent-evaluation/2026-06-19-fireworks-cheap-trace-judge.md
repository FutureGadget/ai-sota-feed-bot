---
title: "A fine-tuned open judge scores production traces at about 1/100th of frontier cost"
date: 2026-06-19
theme: grading-trajectories
evidence: [4235792e910ea51a]
---
LangChain and Fireworks fine-tuned an open model to mine perceived-error signals from production traces, **matching frontier-model judge performance at roughly 1/100th the cost**.

Cost is what kept trajectory grading offline and sampled. A judge this cheap can run over every production trace, which turns evaluation into continuous monitoring rather than a periodic audit.
