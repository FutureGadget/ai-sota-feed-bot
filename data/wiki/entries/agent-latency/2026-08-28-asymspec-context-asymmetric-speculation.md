---
title: "AsymSpec lets the drafter read full context while the verifier decodes a compressed view"
date: 2026-08-28
theme: less-work-per-step
evidence: [aad81dd5a952ad5d]
---
AsymSpec drops speculative decoding's requirement that drafter and target share identical context. A lightweight **drafter reads the agent's full, uncompressed input** while the large verifier decodes from a compressed view, with a divergence-aware acceptance gate keeping verification stable.

It recovers about **90% of full-context accuracy at 1.3-1.7x throughput** and 0.2-0.3x the compute of decoding on full context. That eases the usual trade between compressing a growing agent context for latency and the accuracy compression costs.
