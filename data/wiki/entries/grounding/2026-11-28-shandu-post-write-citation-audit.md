---
title: "Shandu audits every cited sentence after writing and strips citations the source does not support"
date: 2026-11-28
theme: proving-attribution
evidence: [0fe8a1f1febc51fc]
---
Shandu 4.0 is an open-source local deep-research agent. Planning, retrieval, verification, writing, and auditing are separate stages with deterministic Python checks. After the report is written, an auditor checks each cited sentence, bullet, and table row against the evidence behind its `[n]` marker and removes unsupported citations.

Its published sample runs on a cheap non-thinking model show what the audit catches. A 36-source report had **112 supported, 19 partial, 1 removed** citations for $1.22. A 25-source run rated 20 of 121 citations partial. Each model role can be overridden, and the README notes that extraction makes most calls, so a cheap extractor cuts cost.

For builders: a post-write audit pass is a cheap way to make "partially supported" visible in research-agent output.
