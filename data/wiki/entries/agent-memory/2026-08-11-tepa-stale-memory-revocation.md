---
title: "Without revocation, stale memories make an agent worse than having no memory (TEPA)"
date: 2026-08-11
theme: recall-and-curation
evidence: [d7f7f1bf25c4ce76]
---
**TEPA** represents each memory as a keyed precedent and revokes the active one the moment fresher evidence contradicts the same key, so old and new facts never coexist in the retrieval set.

Under full reversal, append-only and last-write-wins caches both score **below no memory at all (0.210 vs. 0.309)**, while TEPA holds **0.950**. A memory layer without revocation is not neutral on stale facts; it actively hurts.
