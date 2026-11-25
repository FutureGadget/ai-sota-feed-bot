---
title: "TACT-Bench: adaptive social engineering adds 17.5% attack-induced failures; tested defenses cut ~9%"
date: 2026-11-25
theme: adversarial-and-security
evidence: [3427f2523e64ffb1]
also: [prompt-injection]
---
TACT-Bench attacks policy-governed tool-use agents through the conversation itself: personas, manipulation tactics, and escalation that adapts to each reply, aimed at an action the hidden policy forbids. Every adversarial task has a benign twin, so the score separates refusing attacks from refusing work. Across 6 assistant models, the base tasks raise attack-induced failure by **17.5%** over four attack baselines; placing a benign task first (*TrustPrime*) adds another **17.0%**. Two tested defenses cut failures by only **8-9%** and did not improve the paired safety-plus-usefulness score.

For builders: test policy enforcement with multi-turn, rapport-building attacks, and score over-refusal on matched benign tasks alongside it.
