---
title: "vLLM v0.24.0 adds MiniMax-M3 with MXFP4, FP8 sparse GQA, and AMD tuning"
date: 2026-06-30
theme: day-0-support
evidence: [6cc910fb018354bf]
---
vLLM v0.24.0 (571 commits from 256 contributors) adds **MiniMax-M3** with a fast follow-on BF16/FP8 indexer, MXFP4 support, FP8 sparse GQA, and AMD/ROCm tuning: MXFP8 MoE on gfx950, FP8 per-channel weights on MI300X, and an FP8 KV-cache fix. It also fixes a MiniMax-M2 performance regression and keeps maturing DeepSeek-V4 support.

New open-weight models arrive with quantized, vendor-specific fast paths in the same release, so self-hosters don't wait for a later optimization pass.
