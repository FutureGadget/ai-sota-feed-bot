---
title: "CordisBench tests whether models can reason about a dynamic harness's component lifecycle"
date: 2026-09-04
theme: measuring-planning
evidence: [27f54a99fd45b38c]
---
Dynamic harnesses let a model change the software that shapes its own execution, so a local plugin change can **propagate through dependencies and cleanup**. **CordisBench** is a 1,200-question benchmark of that lifecycle reasoning, combining a controlled formal setting with real programs.

The harness's own state becomes something the model has to reason about, not just run inside.
