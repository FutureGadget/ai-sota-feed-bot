---
title: "Local CI cuts the feedback loop for developers and coding agents alike"
date: 2026-07-01
theme: beyond-the-engine
evidence: [bbc9b11398e5a4c1]
---
Modern Treasury runs checks on the developer's machine instead of round-tripping to a remote CI runner, cutting feedback latency for **both human developers and coding agents**.

For a coding agent, waiting on a CI runner sits on the same wall-clock budget as each model call. A slow tool round-trip can dominate the loop even when inference is fast.
