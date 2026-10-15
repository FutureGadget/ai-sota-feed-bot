---
title: "Swapping models mid-session carries over the old model's habits unless history is summarized"
date: 2026-10-15
theme: routing
evidence: [5ff62714bccfe1a7]
---
Multi-session agents switch LLMs to balance quality and cost, handing the new model the prior history. Controlled experiments show **behavior transfer**: the recipient adopts reasoning and action patterns from the model that wrote the history. The effect is strongest with raw-history transfer and much weaker after summarization.

The authors' DASH method summarizes with direction and authorship in mind, keeping stronger-model behavior while limiting weak-to-strong transfer. They report it beats raw history and naive summarization across repeated swaps (paper-reported, not independently replicated).

For routers: a cheap-model turn can degrade later expensive-model turns through the shared history.
