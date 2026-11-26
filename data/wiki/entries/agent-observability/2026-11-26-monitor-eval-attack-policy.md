---
title: "A monitor's measured miss rate swung from 0.5% to 20.8% depending on how the attack transcripts were made"
date: 2026-11-26
theme: monitoring-limits
evidence: [4638abcd39a00769]
also: [agent-evaluation]
---
Agent monitors are evaluated on transcripts from attack policies that stand in for real misbehavior. Testing an ex-production OpenAI monitor, the authors found its false-negative rate ranged from **0.5% to 20.8%** across optimization levels of one method (RL), and from **6.4% to 23.0%** across methods. All attacks were built against proxy monitors and transferred to the held-out target. Proxies also leave artifacts, such as reasoning about a side task, that change monitor judgments.

For builders: a monitor that looks strong against basic attacks may not be. Evaluate it against several attack-generation methods at high optimization, and report the worst case.
