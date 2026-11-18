---
title: "A 4B verifier checks 1,000 natural-language policy rules against an agent output in under 2 seconds"
date: 2026-11-18
theme: cheaper-judges
evidence: [2a0be454413b0af8]
also: [agent-reliability]
---
**VFM** is a tree-attention verifier that encodes the shared context once and scores N natural-language criteria in parallel. Each criterion gets its own verdict: satisfied, violated or not applicable. It was pretrained on CriteriaBank, 394K tuples over 321K distinct criteria. The fine-tuned **VFM-4B** beat GPT-5.4 on a synthetic governance benchmark and DynaGuard-4B on DynaBench trace-level failure detection.

On one H100 it scores **1,000 criteria against a 4K-token context in under 2 s using under 11 GB of VRAM**. That puts full-policy checks on every step within runtime budget. Because each verdict names the violated rule, only flagged cases need to go to a larger reasoning judge.
