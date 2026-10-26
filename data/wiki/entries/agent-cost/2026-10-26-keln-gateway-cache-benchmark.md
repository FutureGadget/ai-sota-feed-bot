---
title: "Gateway choice swung agent cache hit rate from 63% to 94% on identical traffic"
date: 2026-10-26
theme: caching-and-serving
evidence: [b7153f0672209bd4]
---
Keln, a gateway vendor, ran 24 hours of agent sessions (13,440 turns, 3,360 per gateway) on DeepSeek V4.1 Flash through OpenRouter :nitro, Vercel, Ramp and Keln, with 1 turn in 20 paused 1 to 20 minutes. Cache hit rates were Keln 94%, OpenRouter 88%, Vercel 87%, Ramp 63% (vendor-reported, self-benchmark).

The gap came from turns that went fully cold after the first, which depends on how each gateway picks a provider. For builders: prompt-cache hit rate is a gateway property, so measure it with your own pause patterns before comparing per-token prices.
