---
title: "Reversing a rubric's score anchors changes LLM judges' verdicts even when the criteria are unchanged"
date: 2026-11-20
theme: scoring-design
evidence: [d59766235f01efbf]
also: [agent-evaluation]
---
This paper tests *semantic faithfulness*: a judge given the same rubric with the scale flipped (5 = worst instead of best) should reach the same verdict. A scale-reversal probe, with floor normalization to separate bias from ordinary run-to-run noise, found **widespread violations across seven open and proprietary judges on five meta-evaluation benchmarks**. Raw agreement under reversal alone was misleading.

Averaging scores from both anchor directions reduced the dependence without hurting agreement with humans. For builders: a judge that correlates with human labels can still be reading the numbers rather than the rubric; run each rubric in both directions and average when the verdict matters.
