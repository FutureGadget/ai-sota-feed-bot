---
title: "Hugging Face trains RL harness adapters that tune an open model to one agent harness and task mix"
date: 2026-11-20
theme: harness-choice
evidence: [701a571706ec6c00]
also: [agent-cost]
---
Hugging Face's harness-adapters post argues that general-purpose models leave accuracy and efficiency unused inside any specific harness. The fix is reinforcement learning on your own task distribution, run *through* the target harness, to produce an adapter for that model-harness pair. The worked example tunes Qwen3.8-27B against Terminal-Bench 2.1.

The point for builders is that harness choice and model choice are no longer separable: an open model adapted to your harness can beat a larger general model on your workload at lower cost. The catch is that the adapter is specific to that harness, so switching harnesses means retraining.
