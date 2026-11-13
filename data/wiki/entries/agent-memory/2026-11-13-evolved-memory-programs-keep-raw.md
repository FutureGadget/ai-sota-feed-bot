---
title: "Evolved memory programs beat hand designs by up to 12 points at 35% of the serving cost"
date: 2026-11-13
theme: architectures
evidence: [61fe6193294930a8]
---
MAPE evolves whole memory programs from minimal seeds through a standard lifecycle interface and a diagnose-propose loop. On LoCoMo and LongMemEval the evolved designs gain up to 12 accuracy points over manually designed baselines at 35% of the serving cost.

Two patterns recur in the winners:

- **Keep raw conversations retrievable.** Extracted memories omit details that the raw turns preserve.
- **Compose retrieved evidence by query intent.** Transplanting this composition module into five existing memory systems improved all five.

Adding serving cost to the search objective moved computation from LLM-based memory construction at write time to selective processing at query time, with competitive accuracy. Paper-reported; code is public.
