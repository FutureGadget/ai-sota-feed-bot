---
title: "Separately distilled 3B memory-writing and retrieval policies reached 73.1% without joint training"
date: 2026-11-24
theme: architectures
evidence: [e5715f39ebf46303]
---
*Composing Independently Distilled Memory and Retrieval Policies* trains a 3B memory writer and a 3B retriever separately, then plugs both into a fixed answer generator. On a LongMemEval-based benchmark the composition scored **73.1%**, against **36.2%** for existing RL-trained memory specialists.

For builders: memory write and memory read can be separate, small, swappable components. That lets you upgrade or audit the retriever without retraining the writer or touching the answering model.
