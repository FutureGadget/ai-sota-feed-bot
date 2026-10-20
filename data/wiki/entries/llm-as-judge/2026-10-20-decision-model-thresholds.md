---
title: "Decision models replace LLM judges only after tuning the 0.50 threshold on your own labels"
date: 2026-10-20
theme: cheaper-judges
evidence: [58b479d20c57cce8]
---
Hamel Husain compared six decision models (Jev, Perplexity Decider, Liquid d1, Cloudflare Clef Flash, OpenAI Decisions) on 100 labeled traces from a leasing agent. The default **0.50 threshold** is often wrong: tuning with cross-validation lifted Liquid d1 and Clef Flash, which otherwise missed his 80% precision and recall floor.

On cost, Perplexity cost 0.82 cents per 100 eval runs at F1 0.79. OpenAI Decisions reached F1 0.87 at 3.72 cents, about 4.5x more. Scores were not calibrated probabilities: one Clef Flash bucket predicted 8% failure but failed 60% of the time. Platt scaling fixed several models, not all. This is one small dataset.

For builders: tune and calibrate the threshold on saved scores before alerting on them.
