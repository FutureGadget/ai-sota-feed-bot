---
title: "Agent memory drops document ACLs: 67% of synthesis tasks leaked in one benchmark"
date: 2026-11-09
theme: memory-integrity
evidence: [42d0d220c3dc643e, c02384b58f1bad50]
---
`sentinel-eval`, a deterministic benchmark and linter, reports that metadata ACL filters in ChromaDB and LlamaIndex block 100% of unauthorized raw-chunk queries, yet cross-document synthesis into shared agent memory leaked confidential parent secrets in 2 of 3 background tasks (67%). A raw chunk keeps its document identity; a synthesized note does not, so the parent permission is lost. Self-reported by a Show HN project, not independently replicated.

MemSeal, a separate Show HN layer, wraps each memory write in a hash-chained provenance envelope (author, source, derivation, trust tier) and gates recall by tier before external sends. Its own evaluation gate is self-reported as failing.

For builders: carry parent ACLs through every derived memory write, or filter at recall by provenance.
