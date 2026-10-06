---
title: "Reasoning effort is becoming a trainable dial that swings token use 25-50%"
date: 2026-07-18
theme: cheaper-models
evidence: [1e95bee9c26709cb]
---
Sebastian Raschka surveys how models learn low/medium/high reasoning modes: system-prompt conditioning, RL with per-token cost coefficients, SFT mixing thinking and non-thinking examples, or distilling several reasoning-depth specialists into one model.

Token consumption swings **roughly 25-50% across effort levels**, and a smaller model at high effort can match a larger one at low effort. Model size and effort have to be tuned jointly, and effort becomes a per-request routing decision based on task complexity.
