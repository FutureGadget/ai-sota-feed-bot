---
title: "Kamera reuses KV cache for repeated frames and screenshots across context shifts"
date: 2026-06-24
theme: caching-and-filtering
evidence: [1c2693c60a919d8d]
also: [agent-cost]
---
Multimodal agents re-examine the same video frames, UI screenshots, and rendered artifacts as their context slides, and every look-back **re-encodes from scratch** because prefix caches only serve reuse at a fixed leading position. Kamera proposes a **position-invariant multimodal KV cache** that reuses those visual tokens across context shifts, training-free.

For agents that loop over visual state, redundant re-encoding is a hidden, fast-growing cost; Kamera turns it into a cache hit.
