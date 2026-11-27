---
title: "Across 66 LLMs, generic router upgrades rarely beat simply using the single best model"
date: 2026-11-27
theme: routing
evidence: [cf660e09947351ea]
also: [agent-benchmarks]
---
The Routeability Audit Protocol (RAP) asks first whether a benchmark leaves any room to route. On coarse-scored suites, many models tie for best, and the single best model leaves little headroom. Across four benchmarks and 66 LLMs, larger embedding sets, dimensionality reduction, abstention, clustering, and stronger regressors did not consistently beat the single best model. Clear gains showed up only in portfolio-dependent Omni-MATH settings; GPQA, MMLU-Pro, and IFEval stayed hard or predictor-sensitive.

For builders: before you trust a router's savings claim, check the tied-best rate and the portfolio on your own traffic. A router that cannot beat "always use model X" only adds a failure point.
