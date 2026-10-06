---
title: "BabelJudge finds position, verbosity, and language bias in trajectory judges"
date: 2026-06-23
theme: grading-trajectories
evidence: [c579e90dd1110817]
---
BabelJudge, an open-source benchmark, measures LLM-as-judge reliability across languages **and agent trajectories**. Judges favor the response in slot A (position bias), prefer longer responses regardless of quality (verbosity bias), and degrade sharply in lower-resource languages — biases raw accuracy hides.

A trajectory judge needs its own validation before its verdicts gate a release.
