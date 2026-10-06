---
title: "Run-to-run noise can exceed the gap between the best and worst model"
date: 2026-07-05
theme: trusting-the-score
evidence: [d8ea565801623af0]
---
Dan Luu's notes on agentic coding measure benchmark variance directly: one model's **run-to-run standard deviation (7.5% on a coding task) exceeded the best-to-worst-model gap**, and swapping a few tasks out of a ~100-task set flipped which model ranked first. Two models can each look cheaper or more expensive than the other depending on the task set.

A leaderboard number is a claim about that task set, not a general fact about the model. Report variance across repeated runs.
