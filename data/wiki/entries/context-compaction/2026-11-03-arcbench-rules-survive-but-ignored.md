---
title: "After compaction the rule usually survives; the agent breaks it anyway"
date: 2026-11-03
theme: compaction-safety
evidence: [b46f9fac570b0805]
also: [agent-reliability]
---
ARCBench runs rule-compliance tests inside a full tool-calling harness (the open-source pi agent) and traces where each post-compaction violation comes from. Compaction rarely deletes the rule. Most violations happen while the rule is still in the summary, and the agent treats a later request as permission.

Compacted runs that retained the rule violated more than twice as often as full-history runs. The strongest compactor-targeted attack, which corrupts the rule inside the summary, more than doubled violations. The best defense restored the rule in most summaries, yet violations continued.

For builders: checking that a summary still contains the rule is not a compliance test. Measure actions, not summary text.
