---
title: "An Evaluation Agent screens retrieved documents for poisoning with NLI checks and a Trust Index"
date: 2026-08-26
theme: adversarial-evidence
evidence: [24ddbe91a622a3cd]
---
RAG systems trust whatever ranks as relevant, but relevance is not truth. This middleware combines NLI fact-checking, a **five-signal poison detector**, and a weighted **Trust Index (0.4 factuality + 0.35 coherence + 0.25 (1 - poison))** with a dampener for heavily contaminated contexts.

- On TruthfulQA it reaches **91% accuracy and 100% recall** on instruction-injection attempts.
- In-place edits such as entity swaps stay hard to catch.
- On FEVER, thresholds need per-model recalibration rather than transferring as-is.

See [prompt injection](/topic/prompt-injection) for the attack side.
