---
slug: speculative-decoding
kind: solution
title: "Speculative decoding: draft cheaply, verify in parallel"
status: active
obstacles: [agent-latency]
related_storylines: []
evidence: [62173e9d865bdec2, 99bd515fd5fd8083, f0c08e4beff850db, b811cc97eff4aae9, aad81dd5a952ad5d, b4fa4d7778a6247d]
updated: 2026-08-27
covers_evidence: [62173e9d865bdec2, 99bd515fd5fd8083, f0c08e4beff850db, b811cc97eff4aae9, aad81dd5a952ad5d, b4fa4d7778a6247d]
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

vLLM's own AMD benchmarking now spans the full method menu, not just EAGLE-3:
native MTP, the Gemma 4 MTP paired checkpoint, EAGLE-3, the parallel-draft
DFlash, and DFlash-plus-Markov-head DSpark, measured on Instinct GPUs, land at
different speedups by model and benchmark — Gemma-4-26B hits 2.87x on MATH500
with DFlash and 2.74x on GSM8K with Gemma 4 MTP, Qwen3.5-122B reaches 2.20x on
MATH500 with native MTP, Kimi-K2.5 hits 2.68x on MATH500 with DFlash, and
Qwen3-8B reaches 1.63x on GSM8K with DSpark. The practical takeaway: tune
`num_speculative_tokens` per workload instead of copying a default — DFlash's
gains typically peak around N=7 — and watch mean accepted length and
per-position acceptance rate, not just end-to-end throughput, to catch a
draft/target pairing that's quietly costing more than it saves.

**The draft/target symmetry assumption itself is now a target for
optimization**: AsymSpec drops the requirement that drafter and verifier see
identical context, letting a lightweight drafter read the agent's full,
uncompressed input while the large verifier works from a compressed context
view, using contrastive δ-fusion of logits and a divergence-aware acceptance
gate to keep verification stable. That recovers roughly 90% of full-context
accuracy at 1.3-1.7x the throughput and 0.2-0.3x the compute cost of decoding
on the full context — a direct answer to
[agent-latency](/topic/agent-latency)'s context-compression-vs-accuracy
tension, where compressing an agent's growing context to control cost
normally costs task accuracy too.

Speculative decoding is also becoming a **day-0 launch feature**, not a
follow-up optimization pass: vLLM v0.26.0 ships MTP=1 speculative decoding
as part of the full support stack for its new Inkling model family from the
first release, alongside base modeling, CUDA graph support, and
quantization — the same "new model, latency-tuned serving on day one"
pattern this page's throughline already tracks, now including the
speculation setup itself instead of adding it later.

## What's new
AsymSpec breaks the standing symmetry assumption that draft and target must
share the same context, letting a lightweight drafter see the agent's full
input while the large verifier decodes from a compressed context view —
recovering about 90% of full-context accuracy at 1.3-1.7x throughput and
0.2-0.3x the compute cost of full-context decoding (see State of the art
above).

Prior update: vLLM v0.26.0 shipped MTP=1 speculative decoding for its new Inkling model
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
