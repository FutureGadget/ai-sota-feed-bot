---
slug: speculative-decoding
kind: solution
title: "Speculative decoding: draft cheaply, verify in parallel"
status: active
obstacles: [agent-latency]
related_storylines: []
evidence: [62173e9d865bdec2, 99bd515fd5fd8083]
updated: 2026-06-30
covers_evidence: [62173e9d865bdec2, 99bd515fd5fd8083]
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

## What's new
Speculative decoding is being reported as a shipping production win, not a paper:
Modal/Decagon document state-of-the-art latencies from a tuned draft/verify
setup, and NVIDIA's DFlash claims up to ~15× on Blackwell by pushing speculation
into the hardware path — evidence the technique is now a co-designed default of
the serving stack rather than an optional optimization.

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
