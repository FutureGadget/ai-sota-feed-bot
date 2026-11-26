---
title: "A source-level audit of SkillsBench finds its per-task skill regressions are within noise"
date: 2026-11-26
theme: trusting-the-score
evidence: [062ca583db2be62b]
---
SkillsBench reported tasks where adding agent skills made results worse. A source-code audit and noise-aware reanalysis finds those per-task regressions are **not statistically significant**, so they do not show that skills cause harm.

For builders: per-task deltas on small agent benchmarks often sit inside run-to-run variance. Before dropping or adopting a skill on a benchmark's word, check how many trials stand behind each task and whether the difference survives a significance test.
