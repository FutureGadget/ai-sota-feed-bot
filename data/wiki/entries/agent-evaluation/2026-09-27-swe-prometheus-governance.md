---
title: "SWE-Prometheus scores agents on improving repository governance, not fixing one issue"
date: 2026-09-27
theme: coding-benchmarks
evidence: [1d237df3dbbefd15]
---
**SWE-Prometheus** gives an agent a repository snapshot and an open-ended objective — find risks, prioritize, verify — scored on six governance dimensions (tests/CI, quality gates, documentation, reproducible environment, dependency security, and more) with paired evidence, clean-environment probes, and two teacher ratings.

- Across 60 repositories and ten models, mean improvement ranges **0.057-0.576**, with behavior breakage of 0-23%.
- A repository-blind template scores 0.272 while improving neither environment nor dependency security anywhere.
- A no-op baseline scores a median of zero, a floor against judges that rate everything improved.
