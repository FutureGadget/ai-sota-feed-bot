---
title: "Harness-only tuning let Nemotron 3 Ultra match Opus 4.8's best run at ~8x lower cost"
date: 2026-07-08
theme: cheaper-models
evidence: [9ff56fe893f2ff23, d950eaa58be54c93]
---
LangChain retuned only the Deep Agents harness (prompts, tool schemas, control flow) around NVIDIA's **Nemotron 3 Ultra** and matched Claude Opus 4.8's best agent run at **roughly 8x lower cost**, with no fine-tuning and no bigger model. NVIDIA's write-up of the same work reports benchmark-leading accuracy for the pairing.

Scaffolding investment pays off on every call the harness handles; a bigger model buys quality per call. Both posts come from parties to the result, so validate on your own tasks.
