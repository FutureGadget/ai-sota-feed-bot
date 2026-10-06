---
title: "vLLM serves the 1T-parameter Inkling on day 0 at 380 tokens/sec per user"
date: 2026-07-16
theme: day-0-support
evidence: [66c593bb8d830d85]
---
vLLM shipped full-feature support for Thinking Machines' **1T-parameter multimodal Inkling** the day it released, with MTP, long-context serving, and parallelism. It reaches **380 tokens/sec per user with speculative decoding versus 140 without** on 4 NVIDIA GB200 GPUs.

New models now get latency-tuned serving at launch, so speculative decoding and parallelism apply from the first day instead of after a follow-up optimization pass.
