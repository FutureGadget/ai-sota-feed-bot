---
title: "SageMaker container image caching speeds scale-out by up to 2x"
date: 2026-06-20
theme: caching-and-filtering
evidence: [e0a1d0978e9e8c3b]
also: [agent-cost]
---
Amazon SageMaker AI added **container image caching** for inference, speeding end-to-end latency during scale-out events by up to 2x for generative AI models.

Cold starts are a fixed cost every scale-out pays. Caching the image means bursty agent traffic spends less time and capacity on instances that are still loading.
