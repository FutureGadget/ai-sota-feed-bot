---
title: "AsymSpec recovers ~90% of full-context accuracy while decoding from compressed context"
date: 2026-08-28
theme: compressed-serving
evidence: [aad81dd5a952ad5d]
also: [speculative-decoding, agent-latency]
---
AsymSpec drops speculative decoding's assumption that drafter and verifier see the same context. A lightweight drafter reads the agent's **full, uncompressed input** while the large verifier decodes from a compressed view, with a divergence-aware acceptance gate keeping verification stable.

It recovers roughly **90% of full-context accuracy at 1.3-1.7x the throughput and 0.2-0.3x the compute** of full-context decoding. Compressing agent context normally costs accuracy; this buys most of it back at the serving layer.
