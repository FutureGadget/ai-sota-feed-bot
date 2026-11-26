---
title: "MINE flags indirect prompt injection in RAG via mutual information and embedding variance, with no training"
date: 2026-11-26
theme: model-defenses
evidence: [f17308e5829a9f75]
---
Prompt-engineering defenses against indirect injection in RAG are often overridden by the injected instruction, and supervised detectors must be trained on known attacks. MINE is a training-free alternative: it scores retrieved content using mutual information and embedding variance to detect injected instructions before they steer the model.

For builders: a training-free detector can sit in the retrieval path without a labeled attack corpus. Treat it as one layer; it does not replace limiting what a retrieved document can make the agent do.
