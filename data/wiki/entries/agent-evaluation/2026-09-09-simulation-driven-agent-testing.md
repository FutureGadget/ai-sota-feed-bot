---
title: "Synthetic personas and trajectory entropy catch multi-turn edge cases before release"
date: 2026-09-09
theme: eval-in-production
evidence: [d2cf19ce4bcb183a]
---
Zhou Yu (Columbia, Arklex AI) argues agents stall in the demo phase because teams grade the final answer and skip the multi-turn path. The proposed fix is **simulation-driven testing**: synthetic user personas and **trajectory entropy** as pre-deployment signals, wired into automated CI/CD to catch edge cases before release.

It is process-over-outcome grading framed as a build discipline for multi-turn agents.
