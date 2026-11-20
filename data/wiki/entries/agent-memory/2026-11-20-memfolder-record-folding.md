---
title: "MemFolder keeps 99% of Mem0's benchmark score with half the memory records"
date: 2026-11-20
theme: architectures
evidence: [d9437d502ba575d9]
also: [context-compaction]
---
Long-lived agents pay twice for a growing store: more records slow retrieval, and longer retrieved units raise prefill cost. MemFolder attacks both. **RecordFolder** groups compatible records by entity, semantic affinity, and time order, then merges them into fewer retrieval units. **ContextFolder** rewrites each group as compact text and re-encodes it when a verification pass cannot recover a key fact.

On Mem0, RecordFolder kept **99.0% of average performance on LoCoMo, PersonaMem, and LongMemEval with 50% fewer records**, 1.9 points above the strongest baseline. For builders: consolidate memory with a check that facts survive the merge, instead of pruning old records and hoping nothing needed is lost.
