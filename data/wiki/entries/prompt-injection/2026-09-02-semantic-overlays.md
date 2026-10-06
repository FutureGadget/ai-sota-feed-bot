---
title: "Semantic Overlays: small adapters on a frozen model make it far less injectable"
date: 2026-09-02
theme: model-defenses
evidence: [958e200401ba64f9]
---
Semantic Overlays are small trained adapters on a frozen model that change how it perceives a piece of its context, pitched as an "NX bit" for prompt injection. The author reports taking a highly injectable Qwen-3.5-9B to **state-of-the-art scores on every prompt-injection benchmark they could find**, without training on the attacks used to test it.

This is a Show HN with a live demo, and the benchmarks cover black-box attacks only. The idea worth tracking is marking context as data inside the model instead of filtering strings in front of it.
