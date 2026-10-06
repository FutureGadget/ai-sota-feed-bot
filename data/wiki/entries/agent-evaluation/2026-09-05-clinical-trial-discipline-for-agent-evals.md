---
title: "Clinical-trial discipline keeps agent eval scores from lying"
date: 2026-09-05
theme: score-validity
evidence: [be2df31b86804088]
---
"How to Design an Agent Evaluation That Doesn't Lie to You" borrows clinical-trial practice: pre-specified metrics, **complete denominators** including failures, separate development and confirmation sets, and fail-closed systems.

It names two ways a score misleads without anyone gaming it:

- A **hidden denominator** — "0/3 scenarios completed" and "1/8 model requests executed" tell different stories.
- Success manufactured through **retries** rather than capability.
