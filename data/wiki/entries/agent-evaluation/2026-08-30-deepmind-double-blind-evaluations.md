---
title: "Double-blind evaluation in confidential computing keeps weights and eval prompts mutually hidden"
date: 2026-08-30
theme: gaming-and-containment
evidence: [f0dc85dcc6d3444f]
---
Google DeepMind piloted **double-blind evaluations**: the model provider and an external evaluator run inside Confidential Computing (Google Cloud's Confidential Space), so the evaluator never sees the weights and the provider never sees the eval prompts. Both sides can verify the separation held through **cryptographic evidence** rather than a policy promise.

Partners included Singapore's AI Safety Institute, OpenMined, AVERI, and MLCommons, against a Gemini Flash Lite model. It makes "the provider peeked at the test" structurally impossible instead of merely discouraged.
