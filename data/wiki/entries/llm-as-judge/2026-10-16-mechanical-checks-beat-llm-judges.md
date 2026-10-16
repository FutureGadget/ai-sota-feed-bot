---
title: "Mechanical checks catch errors LLM judges accept"
date: 2026-10-16
theme: trusting-the-judge
evidence: [12ce418f6930dbfb]
also: [agent-reliability]
---
A paper on verifying Lean autoformalizations pairs an LLM semantic review with **mechanical numerical and vacuity checks**. Statements are checked by computation, not only by a model's reading of faithfulness.

On three labeled datasets the combined method had the lowest accepted-error rate (fraction of incorrect statements it accepted) among the methods the authors evaluated. Expert review also found translation and source defects in existing datasets. Results are paper-reported, in a formal-math domain.

For builders: where a claim can be checked by execution, arithmetic, or a vacuity test, run that check alongside the judge and return its output as checkable feedback. Keep the LLM judge for what only a model can assess.
