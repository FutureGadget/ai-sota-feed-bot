---
title: "Controlled test finds latent agent-to-agent messaging adds nothing over text and can cut accuracy"
date: 2026-11-25
theme: shared-context
evidence: [badad62bfaefb859]
---
Latent interfaces let agents pass continuous representations instead of decoded text, and earlier papers reported gains. **LatentLens** separates the interface from the harness: on seven benchmarks with Qwen3 models, adding it to the same harness did **not** improve accuracy and sometimes degraded it substantially. The representations keep some domain information, but incompatible realignment between agents hurts, and repeated latent steps amplify representation-level errors.

For builders: earlier latent-communication gains likely came from the harness. Keep text handoffs, which are inspectable and debuggable, until a latent channel beats them under a matched harness.
