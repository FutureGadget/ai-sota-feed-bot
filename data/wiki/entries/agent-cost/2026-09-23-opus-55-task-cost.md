---
title: "Opus 5.5's worked numbers: same session costs $11.20 uncached vs $1.62 at 90% hits"
date: 2026-09-23
theme: caching-and-serving
evidence: [3d1eacfa6636ae86, a26eb8af87253d8b]
---
Opus 5.5 lists at **$4/$20 per million input/output tokens** (about 20% below Opus 5), with cache reads at $0.20/Mtok (about 60% cheaper). Anthropic's worked task costs:

- A 2.8M-token session costs **$11.20 uncached vs. $1.62 at a 90% cache-hit rate**.
- A high-effort turn adds about $0.40 of thinking but can avoid a similar-cost retry loop.
- A $0.25 compaction pass pays for itself in about ten turns.

Anthropic says it priced and trained Opus 5.5 for coding sessions that run longer and use more context than at Opus 5's launch.
