---
title: "Favur Evals pairs every harness score with a full replay of the run"
date: 2026-07-21
theme: trusting-the-score
evidence: [13619e816aa57836]
---
Favur is a 14-agent harness (planner, architect, coder, tester, reviewer, builder) coordinated by code, not an LLM. **Favur Evals** scores its runs across models from the same standardized statement of work, using composite engineering subjects computed from each run's own artifacts: lint, test results, tool telemetry.

Every run is captured end to end and can be replayed. Reproducibility becomes a feature of the benchmark rather than a property to demand of it.
