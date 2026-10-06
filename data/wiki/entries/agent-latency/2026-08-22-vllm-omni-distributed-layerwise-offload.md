---
title: "vLLM-Omni streams DiT weights across devices to serve a 124 GB model on 64 GB HBM"
date: 2026-08-22
theme: kv-state
evidence: [a0661b7f263e39ff]
---
vLLM-Omni's **Distributed Layerwise Offload** shards and streams diffusion-transformer weights across devices. It serves a measured 124 GB Cosmos3 model on 64 GB of HBM and estimates a path toward 200B+ parameter models.

It applies the offload-instead-of-fit approach to model weights rather than KV state: memory capacity, not compute, decides which models fit a given fleet.
