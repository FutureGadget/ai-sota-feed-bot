---
title: "Elastic's code-optimization agent is gated by paired trials, significance tests, and human approval"
date: 2026-09-18
theme: trusting-the-score
evidence: [58e167770f5901f7]
---
Elastic's harness lets an agent propose Elasticsearch performance optimizations through exploration, exploitation, and validation phases. Trust comes from statistics, not one before/after run:

- **Paired stash-flip trials** cancel thermal drift.
- A Mann-Whitney U test plus seeded bootstrap CI, with the fork as the statistical unit.
- An accept bar set by each benchmark-machine pair's A/A noise floor.
- Guard workloads, an allocation check against wins bought with ~15% extra garbage, and add-only tests.

Humans approve benchmark registration, promotion, and publication.
