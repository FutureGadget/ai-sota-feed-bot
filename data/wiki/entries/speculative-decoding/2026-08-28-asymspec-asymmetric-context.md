---
title: "AsymSpec lets the drafter read full context while the verifier decodes a compressed view"
date: 2026-08-28
theme: agent-context
evidence: [aad81dd5a952ad5d]
---
AsymSpec drops the assumption that drafter and verifier share identical context. A lightweight drafter reads the agent's full, uncompressed input; the large verifier works from a compressed view. Contrastive δ-fusion of logits and a divergence-aware acceptance gate keep verification stable.

The paper reports roughly **90% of full-context accuracy at 1.3-1.7x throughput and 0.2-0.3x the compute** of full-context decoding. That targets the agent trade-off where compressing a growing context to control cost usually costs task accuracy too. It is a research result, not yet a serving-framework feature.
