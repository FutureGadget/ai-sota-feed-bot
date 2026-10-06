---
title: "AutoViewMem self-configures several views of the same memory and picks one per query"
date: 2026-09-23
theme: recall-and-curation
evidence: [eddc39b344540bb2]
---
**AutoViewMem** argues that fixed granularities and static schemas fail when preferences, events, constraints, and temporal updates share one mixed representation; the interference makes top-K retrieval noisy.

Instead of one index, it maintains several complementary projections of the stored history and chooses which view to query per request. Like CABLE, it locates recall failures in the query interface, not only in what is stored.
