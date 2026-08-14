---
slug: speculative-decoding
kind: solution
title: "Speculative decoding: draft cheaply, verify in parallel"
status: active
obstacles: [agent-latency]
related_storylines: []
evidence: [62173e9d865bdec2, 99bd515fd5fd8083, f0c08e4beff850db, b811cc97eff4aae9, edc5b011f192f53b, 80e7ec208d50f270]
updated: 2026-08-14
covers_evidence: [62173e9d865bdec2, 99bd515fd5fd8083, f0c08e4beff850db, b811cc97eff4aae9, edc5b011f192f53b, 80e7ec208d50f270]
---

## TL;DR
Generate several candidate tokens cheaply with a small *draft* model (or a
lightweight head), then let the full model verify them in a single parallel
forward pass — accepted tokens come "for free," so latency drops without
changing the output distribution. It attacks the one term raw engine tuning
can't: the strictly sequential, one-token-at-a-time decode that dominates an
agent's wall-clock.

## State of the art
Speculative decoding has moved from a research trick to a serving default, and
the recent work is about making the draft step both cheap and accurate enough
that the acceptance rate justifies the extra verify compute. Modal and Decagon
report state-of-the-art inference latencies in production by tuning the
draft/verify pair to their workload, framing it as a practical, deployable win
rather than a benchmark curiosity. On the hardware side, NVIDIA's DFlash pushes
the technique into the silicon — up to ~15× inference-performance gains on
Blackwell — showing the draft-and-verify pattern is being co-designed with the
accelerator, not just layered on top in software. The throughline is that the
gains are largest exactly where agents hurt most: long, latency-sensitive decode
loops where shaving sequential steps compounds across every turn of the agent.

The hardware co-design push is no longer NVIDIA-only: AMD's Quark now trains,
quantizes, and serves EAGLE-3 draft models with vLLM on Instinct GPUs,
reporting up to 2.00× throughput for Kimi-K2.5 and 1.79× for MiniMax-M2.5 —
evidence the draft-and-verify pattern is becoming a cross-accelerator serving
default rather than a technique tied to one vendor's silicon.

Speculative decoding is also becoming a **day-0 launch feature**, not a
follow-up optimization pass: vLLM v0.26.0 ships MTP=1 speculative decoding
as part of the full support stack for its new Inkling model family from the
first release, alongside base modeling, CUDA graph support, and
quantization — the same "new model, latency-tuned serving on day one"
pattern this page's throughline already tracks, now including the
speculation setup itself instead of adding it later.

The verification budget itself is becoming adaptive rather than fixed: vLLM's
DSpark sizes the draft-verification budget from per-request confidence
instead of verifying every drafted token, so one deployment configuration
holds the throughput/latency frontier across the whole batch-size range
(1 to 256) instead of needing separate tuning per load level.

Diffusion-based drafting is also picking up a correction mechanism that
scales past a single draft chain: DARTree extends a pretrained
autoregressive correction head from chains to trees — building a
fixed-width candidate tree in one batched pass, then best-first-pruning it
down to the verification tree — and reports the highest average acceptance
length across seven math/code/chat benchmarks, accepting up to 12.97 tokens
per verification round (98.6% more than DFlash, 27.9% more than Domino in
the same setting) for up to 9.73x lossless speedup over autoregressive
decoding.

## What's new
DARTree extends autoregressive draft-correction from chains to trees for
diffusion-based drafting, reporting up to 12.97 accepted tokens per
verification round and up to 9.73x lossless speedup — a training-free
technique that beats prior tree methods (DFlash, Domino) on acceptance
length. vLLM's DSpark separately makes the verification budget itself
adaptive, sizing it from per-request confidence so one configuration holds
the throughput/latency frontier across the full batch-size range instead of
retuning per load level.

Prior update: vLLM v0.26.0 ships MTP=1 speculative decoding for its new Inkling model
family as part of the model's initial full support stack (alongside base
modeling, CUDA graph support, and quantization) rather than as a later
optimization pass — evidence that draft-and-verify setup is now planned
into a new model's launch, not bolted on after.

## Trade-offs
Lossless by construction — the full model still verifies every token, so quality
is unchanged — but the win is entirely a function of **acceptance rate**: if the
draft and target disagree often (out-of-distribution inputs, a poorly matched
draft model), you pay for the draft *and* the verify and can come out slower.
It costs extra memory and serving complexity (a second model or draft head to
host and keep in sync), and the speedup is real on decode-bound, long-output
work but marginal on short replies or prefill-bound prompts. Best treated as a
serving-layer knob tuned to the actual workload — which is why workload
characterization ([agent-latency](/topic/agent-latency)) and speculation are
complementary, not alternatives.

## Why it matters for platform engineers
It is one of the few latency levers that doesn't force a quality trade — the
output is identical to greedy/sampled decoding from the target model, so it's
safe to enable broadly once the draft pairing is tuned. For agent traffic, where
the same sequential decode is paid on every loop step, the per-call saving
compounds across the run, making it a high-leverage default to validate against
your own traces before reaching for a smaller, lossy model.
