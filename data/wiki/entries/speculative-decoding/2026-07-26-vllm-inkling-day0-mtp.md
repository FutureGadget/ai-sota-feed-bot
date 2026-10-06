---
title: "vLLM v0.26.0 ships MTP speculative decoding as part of a new model's day-0 support"
date: 2026-07-26
theme: serving-default
evidence: [b811cc97eff4aae9]
---
vLLM v0.26.0 adds the Inkling model family with a full support stack in the first release: base modeling, piecewise CUDA graphs, LoRA, NVFP4 quantization, and **MTP=1 speculative decoding**.

Speculation is now planned into a model's launch rather than added in a later optimization pass. When you adopt a new model on vLLM, check whether its speculation path is already supported before building your own draft setup.
