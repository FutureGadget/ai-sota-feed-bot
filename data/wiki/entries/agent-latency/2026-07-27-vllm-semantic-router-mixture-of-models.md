---
title: "vLLM Semantic Router reframes routing as a Mixture-of-Models engine"
date: 2026-07-27
theme: agent-traffic
evidence: [aba45d95421e53e0]
---
At 5,000 GitHub stars, vLLM Semantic Router sets its next phase: building the **training, evaluation, and inference engine for a Mixture-of-Models** era.

"Which model handles this request" becomes a first-class serving-layer decision with its own eval loop, not a routing feature bolted onto an engine. For agents, that is where fast-and-cheap versus slow-and-capable gets decided per call.
