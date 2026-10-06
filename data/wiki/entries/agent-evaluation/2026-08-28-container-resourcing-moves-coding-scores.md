---
title: "Container resource settings move agentic coding scores by up to 6 points"
date: 2026-08-28
theme: score-validity
evidence: [c78d84ac1a7e3d92]
---
Anthropic measured a **6-percentage-point gap on Terminal-Bench 2.0** (and 1.54 points on SWE-Bench at 5x baseline RAM) between the most- and least-resourced container setups — variance that can exceed the gap between top leaderboard entries.

The cause: setting the guaranteed allocation equal to the hard kill threshold lets transient memory spikes crash runs, a **5.8% infrastructure-error rate**. A calibrated gap (3x ceiling multiplier) cut errors to 2.1% and kept legitimate score changes within noise. Pin and report resource enforcement config alongside model and task set.
