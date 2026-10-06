---
title: "Similarweb's first report rubric rewarded source quantity until it was recalibrated"
date: 2026-07-29
theme: grading-trajectories
evidence: [59cb16803d591ef4]
also: [llm-as-judge]
---
Similarweb grades long-form Deep Research reports in LangSmith against quality-dimension rubrics with explicit **scoring anchors** (e.g. `source_integration`: 0.0 for a single data API, 1.0 for extensive attributed sources), plus faithfulness checks for ungrounded claims, A/B comparison against saved baseline runs, and trace-linked feedback that ties a low score to the offending step.

The first rubric **rewarded source quantity over quality**. It became reliable only after recalibration to reward named, relevant sources tied to specific claims — a plausible rubric can score the wrong thing until checked.
