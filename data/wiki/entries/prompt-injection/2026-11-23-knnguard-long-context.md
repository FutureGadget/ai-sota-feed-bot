---
title: "A training-free injection guardrail fell to near-chance AUROC on prompts over 1,000 tokens"
date: 2026-11-23
theme: model-defenses
evidence: [817153b1ff39da26]
---
An audit of kNNGuard, which flags injections by nearest-neighbour similarity to a bank of known attacks, found its AUROC drops to about **0.55** on inputs longer than 1,000 tokens, close to a coin flip. The authors test three fixes: length-routed example banks, a long-context embedding model, and strided window pooling over the input.

For builders: agent inputs (tool results, retrieved pages) are usually long, while guardrail benchmarks are short. Re-test any embedding-based detector at your real input length before trusting it.
