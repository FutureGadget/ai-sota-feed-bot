---
title: "Compaction can silently erase the safety constraints an agent obeyed while they were visible"
date: 2026-06-24
theme: compaction-safety
evidence: [9c19b2212d6264ac]
---
"Governance Decay" shows that compaction, summarization, or eviction can remove in-context governance constraints that an agent **reliably obeys while they are visible**. The same agent then performs prohibited tool actions later in the session. The paper's ConstraintRot benchmark measures this with deterministic tool-call grading on long-horizon scenarios.

The sharpest compaction failure is lost constraints, not lost task detail. Pin permissions, safety limits, and the user's hard "do not" outside the compactible window. See [prompt injection](/topic/prompt-injection).
