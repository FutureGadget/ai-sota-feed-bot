---
title: "A 77% average pass rate hides a 53% pass-every-time rate; episodic guidelines close part of the gap"
date: 2026-09-13
theme: consistency-and-autonomy
evidence: [c47e9befb61fd48e]
---
On AppWorld, a ReAct agent on GPT-4.1 run five times on the same task succeeds on **every run only 53%** of the time, though its per-run pass rate averages **77%**. The authors call the 24-point shortfall the **consistency gap**.

Their fix: a Consistency Analyzer flags the trajectory steps most likely to flip between runs, and a Guideline Generator writes a targeted guideline into episodic memory for similar future tasks. All-five-runs success rose **16 points** on seen tasks and **13 points** on unseen similar ones.

For unattended use, measure pass-every-time, not average pass rate. See [agent memory](/topic/agent-memory) for the storage side.
