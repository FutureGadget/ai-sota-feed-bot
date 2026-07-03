---
slug: agent-latency
kind: obstacle
title: "Agent loops multiply per-call latency into slow, expensive runs"
area: latency
status: active
solutions: [speculative-decoding, context-compaction]
obstacles: []
related_storylines: []
evidence: [0ca61ed96ddd38e5, e313a171aa375adf, 537f21de13e2a85a, c66b542cadbb4592, 6cc910fb018354bf, e2f43565cf7c0d8e, dca39fe0489bebd0, 0933879c19d86a9c, bbc9b11398e5a4c1, c0c3ec4a6aba7980, d3e345ae085932a6]
updated: 2026-07-03
covers_evidence: [0ca61ed96ddd38e5, e313a171aa375adf, 537f21de13e2a85a, c66b542cadbb4592, 6cc910fb018354bf, e2f43565cf7c0d8e, dca39fe0489bebd0, 0933879c19d86a9c, bbc9b11398e5a4c1, c0c3ec4a6aba7980, d3e345ae085932a6]
---

## TL;DR
A chatbot waits on one model call; an agent waits on *many*, in sequence —
plan, call a tool, read the result, decide again — so the wall-clock a user
feels is the per-token decode latency multiplied by the loop length, and a
serving stack tuned for single-shot throughput can still leave an agent feeling
slow. Latency is the run-time twin of [cost](/topic/agent-cost): the same loop
that runs up the bill also runs out the clock.

## State of the art
Latency for agents is being attacked at the **serving layer** and the
**workload-shape layer** at once. The serving engines that host agent traffic
are competing hard on decode latency and throughput — vLLM's v0.24.0 line keeps
adding fast model support and quantized indexers, Modular's 26.4 ships
state-of-the-art MoE serving, and infra partnerships (NVIDIA + AWS) are pitched
explicitly on "low-latency inference at scale" — but raw engine speed only moves
one term in the agent's latency budget. The newer recognition is that **agent
workloads do not look like chat**: coding agents issue bursty, long-context,
tool-interleaved requests, and characterizing that shape is now its own research
target (TraceLab profiles real coding-agent workloads for LLM serving so the
server can be tuned to them rather than to a generic chat trace). That work is
surfacing agent-specific bottlenecks the chat era never hit — DualPath finds the
binding constraint in agentic inference is **storage bandwidth**, not compute,
because the agent's growing KV/context state has to be streamed back each step —
and one direct answer is shrinking that state: RaBitQCache uses randomized
rotated binary quantization to compress the KV cache and an adaptive top-p token
budget instead of a fixed top-k, cutting the memory-I/O DualPath identifies as the
bottleneck while holding generation quality. The dev-loop side of latency counts
too: local CI (running checks on the developer's machine instead of round-tripping
to a remote runner) cuts the feedback loop for both human developers and coding
agents, since round-trip time to a CI runner is on the same wall-clock budget as
each model call.
The other lever is the model itself: latency-first small models (Kog's Laneformer
2B, built for its inference engine) trade frontier breadth for predictable speed
on the bulk of an agent's calls, the same downshift logic that drives cost.
Latency also has a hard product floor in interactive modes — a voice agent that
pauses too long gets hung up on, which is why low-latency voice stacks (Loka on
Amazon Nova 2 Sonic) treat round-trip time as a first-class design constraint,
not a tuning afterthought.

The serving layer itself is starting to absorb **agentic behavior**: vLLM's
Semantic Router turns its `vllm-sr/auto` routing feature into a bounded
"micro-agent" runtime — confidence scoring, ratings, and workflow fusion happen
*inside* the serving layer rather than in a separate orchestration hop above
it, collapsing a round-trip that would otherwise cost a full extra model call
and its latency.

## What's new
The framing is shifting from "make the model faster" to "make the *agent
workload* faster." TraceLab characterizes real coding-agent serving traces so
engines can be tuned to bursty long-context tool loops, and DualPath identifies
storage bandwidth — not GPU compute — as the bottleneck in agentic inference,
because the per-step context state has to be moved, not just computed. RaBitQCache
now gives that bottleneck a direct mitigation: quantizing the KV cache with an
adaptive token budget cuts the memory-I/O DualPath flags, without a fixed
top-k retrieval's static waste. A newer move pushes lightweight agentic logic
*into* the serving layer itself — vLLM's Semantic Router runs confidence
scoring and workflow routing as a bounded micro-agent inside the serving
process, avoiding a separate orchestration round-trip's latency cost.
Alongside, latency-first small models (Kog Laneformer 2B) and low-latency
interactive stacks (Loka's Nova 2 Sonic voice agent) show the field treating
round-trip time as an architecture constraint rather than a knob, and the same
instinct is reaching the dev loop itself — local CI cuts feedback latency for
developers and agents alike.

## Why it matters for platform engineers
Latency is where the agent's architecture meets the user's patience and the
GPU's bill — the three trade against each other directly. The job is to budget
latency across the *whole loop*, not per call: count the sequential model hops,
push what you can to a faster or smaller model, cut the tokens that have to be
decoded and streamed each step (compaction, KV reuse), and pick a serving engine
tuned to the bursty, long-context shape agents actually produce rather than to a
chat benchmark. Interactive modes (voice, live coding) set a hard ceiling, so the
deliverable is a latency budget you can reason about per task, not a one-time
inference optimization.
