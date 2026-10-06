---
title: "LangChain treats improving agents as data mining over traces, not labeling"
date: 2026-07-07
theme: grading-trajectories
evidence: [4a0a79e7203bae64]
---
LangChain's loop: mine production agent traces for **failure clusters** first, fine-tune a judge on those clusters (cheaper than a frontier judge), then use that judge to hill-climb agent performance with evals.

"What should we evaluate" becomes a question the traces answer, rather than a rubric written before any traces existed.
