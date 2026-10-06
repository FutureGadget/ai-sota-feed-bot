---
title: "Evaluators can keep the right verdict while their reasons stop tracking the evidence"
date: 2026-08-26
theme: grading-trajectories
evidence: [fe206f2a71d579f8]
also: [llm-as-judge]
---
"No Judgment Without a Reason" formalizes evaluator accountability (grounds, norms, authority) and defines **judgment receipts**: minimal source-replacement sets that reproduce a revised verdict. On ReasonBench (19,520 cases, 7,200 controls):

- A small model hits **98.41%** receipt accuracy on frozen evaluations.
- Meaning-preserving permutations of the same sources drop valid receipt recovery to 54.8-49.2%.
- A model retrained on single-source changes keeps 93.75% verdict accuracy but recovers only **7.16%** of receipts on multi-source updates.

Label accuracy alone does not show an evaluator is judging for the right reasons.
