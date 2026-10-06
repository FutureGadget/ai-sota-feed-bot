---
slug: speculative-decoding
kind: solution
title: "Speculative decoding: draft cheaply, verify in parallel"
status: active
obstacles: [agent-latency]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: serving-default
    title: Speculation as a production serving default
    summary: Speculative decoding now ships in production stacks and in a new model's day-0 vLLM support, with gains tuned to each team's own traffic.
  - key: draft-methods
    title: Picking and tuning the draft method per model and accelerator
    summary: MTP, EAGLE-3, DFlash, and DSpark now run on both NVIDIA and AMD GPUs; the fastest method changes by model and task, so tune and measure acceptance per workload.
  - key: agent-context
    title: Speculation for long agent contexts
    summary: Research now lets drafter and verifier see different context, aiming to keep full-context accuracy while the expensive model decodes a compressed view.
---

## TL;DR
Generate several candidate tokens cheaply with a small *draft* model (or a
lightweight head), then let the full model verify them in a single parallel
forward pass. Accepted tokens come "for free," so latency drops without
changing the output distribution. It attacks the strictly sequential,
one-token-at-a-time decode that dominates an agent's wall-clock.

## State of the art
Speculative decoding has moved from a research trick to a serving default.
vLLM ships it as part of a new model's day-0 support, and production teams
report state-of-the-art latency by tuning the draft/verify pair to their own
traffic.

**The draft method is now a per-workload choice.** Native MTP heads, trained
EAGLE-3 drafts, and parallel drafters such as DFlash and DSpark all run on
both NVIDIA and AMD accelerators. Benchmarks show the fastest method changes
by model and task, with typical speedups of 1.6-2.9x. Vendor headline numbers
(up to 15x) are ceilings, not planning figures.

**Acceptance rate is the number that matters.** The consensus practice is to
tune `num_speculative_tokens` per workload and watch mean accepted length and
per-position acceptance, not only end-to-end throughput. A poorly matched
draft pays for drafting and verification and can come out slower.

**The open problem is long agent context.** Agents compress growing context to
control cost and lose accuracy doing it. Asymmetric schemes, where a cheap
drafter reads the full input and the verifier decodes a compressed view, are
the current research answer. They are not yet a framework feature.

## Trade-offs
Lossless by construction: the full model still verifies every token, so
quality is unchanged. The win depends entirely on **acceptance rate**. If draft
and target disagree often (out-of-distribution inputs, a poorly matched draft
model), you pay for the draft *and* the verify and can come out slower.

It costs extra memory and serving complexity: a second model or draft head to
host and keep in sync with the target. The speedup is real on decode-bound,
long-output work but marginal on short replies or prefill-bound prompts.

Treat it as a serving-layer knob tuned to the actual workload. Workload
characterization ([agent latency](/topic/agent-latency)) and speculation are
complementary, not alternatives.

## Why it matters for platform engineers
It is one of the few latency levers that doesn't force a quality trade: the
output matches what the target model would produce alone, so it is safe to
enable broadly once the draft pairing is tuned.

For agent traffic, the same sequential decode is paid on every loop step, so
the per-call saving compounds across a run. Validate it against your own traces
before reaching for a smaller, lossy model, and add acceptance rate to your
serving dashboards alongside TTFT and throughput.
