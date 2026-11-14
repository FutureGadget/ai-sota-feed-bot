---
title: "Flex-tier inference cut coding-agent request cost for under half a second of added median latency"
date: 2026-11-14
theme: caching-and-serving
evidence: [076bcadf42543fda]
---
Tesseracted Labs runs its coding agents on an ensemble of models through Doubleword, and its harness extension uses discounted flex inference by default. The team reports saving over 50% on inference requests over several months.

In a small controlled comparison of realtime and flex on the same model, flex's published token rates were 24-27% lower. Estimated request cost was lower in every matched pair, and median end-to-end response time rose by less than half a second. The author calls this a snapshot, not a general result, and publishes runnable examples.

For builders: most agent steps are not latency-critical. Make delayed-capacity tiers the harness default, and reserve realtime for turns where a person is waiting.
