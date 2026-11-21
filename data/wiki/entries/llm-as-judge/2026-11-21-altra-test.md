---
title: "AltRA-Test checks whether an LLM can replace a human annotator using about 100 items"
date: 2026-11-21
theme: trusting-the-judge
evidence: [7ebbec301149b2cc]
---
AltRA-Test extends the Alternative Annotator Test to datasets where different items were labeled by different people. It bootstraps items, swaps one of k human labels for the LLM's, and supports replacement only when the mixed panel's inter-annotator agreement is **statistically non-inferior** to the all-human panel.

Across 18 LLMs, 5 prompting techniques, and 20 datasets, **about 100 items often suffice**, and LLMs pass in **about half** of the setups, mainly depending on the task. For builders: before swapping human graders for a judge, run a non-inferiority test on your own labeled sample; replacement is justified per task, not per model.
