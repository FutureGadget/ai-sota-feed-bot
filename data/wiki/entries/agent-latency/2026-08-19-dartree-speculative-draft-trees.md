---
title: "DARTree drafts token trees for up to 9.73x lossless speculative-decoding speedup"
date: 2026-08-19
theme: less-work-per-step
evidence: [80e7ec208d50f270]
---
DARTree extends a pretrained autoregressive correction head for diffusion drafters from single draft chains to **draft trees**, scoring and pruning candidates across the whole tree in one batch.

Across seven math, code, and chat benchmarks it accepts up to **12.97 tokens per verification round** (98.6% more than DFlash, 27.9% more than Domino), for up to 9.73x lossless speedup over plain autoregressive decoding. It is training-free. Mechanics: [speculative decoding](/topic/speculative-decoding).
