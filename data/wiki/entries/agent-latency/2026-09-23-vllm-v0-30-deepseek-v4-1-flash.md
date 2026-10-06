---
title: "vLLM v0.30.0 adds DeepSeek-V4.1-Flash with its whole KV cache in MXFP8"
date: 2026-09-23
theme: day-0-support
evidence: [3762ff1d2e307774]
---
vLLM v0.30.0 (762 commits from 315 contributors) adds **DeepSeek-V4.1-Flash** with its entire KV cache stored in MXFP8 through a FlashMLA V4.1 speedup on SM100, plus GLM-5.3-Flash, K2-Horizon, and other new models. The release also adds a "Fast Start" path that trims cold-start time.

It is the routine, compounding kind of serving gain: a new model arrives with a lower-precision KV cache and a faster attention kernel in the same release.
