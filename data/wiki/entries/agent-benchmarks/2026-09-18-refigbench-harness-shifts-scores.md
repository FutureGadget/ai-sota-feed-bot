---
title: "ReFigBench: the same model gains in one harness and loses in another"
date: 2026-09-18
theme: trusting-the-score
evidence: [8953d96ac6a84322]
---
**ReFigBench** has coding agents reconstruct 1,000 real arXiv overview figures as editable PowerPoint slides. It runs the strongest model inside two commercial harnesses under two workflows (direct code generation and a specialized PPTX pipeline), ten configurations in all.

The same model **gains from the specialized workflow in one harness and loses in the other**, and harness choice shifts scores even under an identical prompt. It is a measured instance of the protocol-validity critique: score differences reflect the harness, not only the model.
