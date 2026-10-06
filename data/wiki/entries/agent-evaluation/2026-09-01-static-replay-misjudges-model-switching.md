---
title: "Static replay mispredicts model-switching outcomes; forked rollouts are needed"
date: 2026-09-01
theme: score-validity
evidence: [4e6b8920803e5949]
---
Static replay evaluates a model switch by splicing a different model's output into a logged trajectory. Branching-rollout tests on live SWE-bench trajectories (~900 rollouts) show the assumption fails:

- Post-fork actions diverge from the log **61-94%** of the time; patch similarity falls to 0.00-0.11.
- All five success/failure flips came from swap forks; zero across 359 same-model controls.
- Temperature-0 determinism depended on quantization: FP8 controls diverged on 90%+ of forks, AWQ stayed near-identical.

Fork and re-run the environment per model instead of replaying logs.
