---
title: "REVA reuses past attention traces to compress RAG context 5-15x faster than per-query compressors"
date: 2026-09-16
theme: context-budget
evidence: [bf9796fab67d335f]
---
REVA treats RAG compression as data mining: it aggregates a generator's historical query-document attention into a **document-keyed, budget-agnostic score store**, then renders plain-text views at any budget while keeping document order and the standard RAG interface.

The authors show existing compressors gain unstably over simple truncation and can add latency. REVA improves quality **1.0-5.8 points** over them, cuts compression overhead **5.3x-15.6x**, and adds under 40ms.
