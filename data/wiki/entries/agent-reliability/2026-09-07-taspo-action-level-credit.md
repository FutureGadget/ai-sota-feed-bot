---
title: "TASPO assigns per-action credit from verified runs and beats GRPO by 10.6%"
date: 2026-09-07
theme: verifying-the-work
evidence: [8a8b7100027de272]
---
Outcome-based agentic RL applies one verified success or failure signal to every step of a long trajectory. **TASPO** converts privileged supervision from verified successful runs into **per-action credit weights** that are positive, bounded, and mean-preserving, so the verified outcome still sets the update's direction and scale.

Across three agentic benchmarks it improves **10.6% over GRPO** and generalizes better to unseen tasks. Some "confident but wrong" behavior traces back to how the policy was trained, not only to which checks run on its output.
