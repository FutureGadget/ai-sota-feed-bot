---
title: "Async trace anomaly detection flagged 87% of executed goal hijacks but caught 4 of 18 memory-poisoning runs"
date: 2026-11-14
theme: harness-controls
evidence: [d99b7127f7fd99e6]
also: [agent-observability]
---
Google ran Agent Anomaly Detection, which reads agent traces and logs asynchronously and adds no request latency, unchanged against five public agent-security benchmarks it did not write. Four hide the harmful instruction in tool output; one asks for harm directly.

All figures are vendor-reported:

- The model itself refused three in four direct harmful requests and ignored or failed about 30% of injected instructions.
- Of the attacks that did execute, the detector flagged **87%** for post-execution review.
- False alarms ran 2% to 16% of benign sessions, depending on the agent's tools.
- Instructions planted in long-term memory were the gap: **4 of 18** caught.

For builders: an after-the-fact monitor is a review queue. Pair it with a pre-execution boundary, and audit what gets written to memory.
