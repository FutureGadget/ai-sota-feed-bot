---
title: "TASK memory adds activation steering and a removable edit to text notes, cutting memory-ignoring errors"
date: 2026-11-26
theme: memory-integrity
evidence: [69a487d02c92b580]
---
Text-only memory fails at use time: the model has the note in context and still answers from its prior. TASK memory stores each memory as a text note plus an activation-steering vector and a removable knowledge edit on a frozen model. The authors report memory-ignoring errors at **at most 1.5%** across ten model-dataset cells.

For builders: this needs weight or activation access, so it applies to self-hosted open models, not API models. The "removable" edit is the operationally important part: memories can be deleted without retraining.
