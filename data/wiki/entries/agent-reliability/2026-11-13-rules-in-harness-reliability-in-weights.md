---
title: "Skill rules add policy knowledge a small agent lacks; RL on its own logs makes solved tasks repeatable"
date: 2026-11-13
theme: consistency-and-autonomy
evidence: [bdf2dbbea35477e7]
---
A Gemma 4 12B customer-service agent improved from its own deployment logs with no stronger teacher model, using two separate levers.

- **Harness:** the model diagnoses failed conversations and writes rules into on-demand skills. A rule survives only after code checks, counterexample self-review, a paired retest, and a noise-calibrated validation gate.
- **Weights:** GRPO trains a LoRA adapter on complete multi-turn tool-using conversations.

After two rounds on τ²-bench, pass^1 rose 12.5 points in retail and 19.5 in airline; pass^4 rose 18.4 and 22.0. A 2x2 ablation separates the effects: rules rescue tasks the agent never solved, and trained weights make already-solved tasks consistent. RL with the rules in context did not internalize the policy knowledge. Paper-reported.
