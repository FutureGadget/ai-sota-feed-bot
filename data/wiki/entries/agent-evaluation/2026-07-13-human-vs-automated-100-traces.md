---
title: "Checking 100 human-annotated traces shows automated evals diverge from human raters"
date: 2026-07-13
theme: grading-trajectories
evidence: [05a8c95d74885091]
also: [llm-as-judge]
---
In his AI product engineering notes, Hamel Husain checked **100 human-annotated traces** against automated eval systems and found real divergence between what the automated pipeline scored and what a human rater would.

You cannot certify an automated eval suite by spot-checking a few cases. Measure its agreement with human judgment directly, and re-measure when the judge, rubric, or traffic changes.
