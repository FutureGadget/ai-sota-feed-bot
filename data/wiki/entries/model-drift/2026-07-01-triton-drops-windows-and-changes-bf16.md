---
title: "Triton 2.70 drops Windows support and changes BF16 handling in its client"
date: 2026-07-01
theme: serving-runtime-drift
evidence: [b78fb2c666f0c2da]
---
Triton Inference Server 2.70.0 (NGC 26.06) is a **breaking release**: it removes the Windows server build, and its Python client's BF16 handling now requires `ml_dtypes`.

Runtime drift can be outright breaking, not only behavioral: a bump can remove a deployment target or break client code that never touched the model.
