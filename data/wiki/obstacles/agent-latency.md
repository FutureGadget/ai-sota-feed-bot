---
slug: agent-latency
kind: obstacle
title: "Agent loops multiply per-call latency into slow, expensive runs"
area: latency
status: active
solutions: [speculative-decoding, context-compaction]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-11-25
themes:
  - key: agent-traffic
    title: Scheduling, batching, and routing for agent-shaped traffic
    summary: Agent traffic is bursty, long-context, and cache-heavy; session-aware scheduling, learned batching, and routing inside the serving layer beat chat-tuned defaults, and the levers compound when tuned together.
  - key: kv-state
    title: "KV state: compress it, offload it, shard it, reuse it"
    summary: Moving the agent's growing KV state is the bottleneck; quantization, shared RAM/NVMe tiers, context parallelism, and prefix-aware routing cut it, but reuse outside a clean prefix needs repair.
  - key: engine-architecture
    title: Disaggregated and specialized serving engines
    summary: Engines now split serving by phase (prefill/decode) and by compute type (attention/FFN), add hardware-specific kernels, and are what large deployers run in production.
  - key: day-0-support
    title: Day-0 serving for new models and hardware
    summary: New open-weight models and accelerators get quantized, speculative, disaggregated serving at launch, followed by steady per-release kernel gains of a few percent per token.
  - key: less-work-per-step
    title: "Less work per step: small models, shorter prompts, faster drafting"
    summary: Latency-first small models, learned prompt compression, protocol-aware trimming, and better speculative drafting cut decode work; trimming below half the context budget sharply raises failure.
  - key: beyond-the-engine
    title: "Latency outside the model: tools, cold starts, and voice"
    summary: Tool round-trips, verification runs, and cold starts often dominate wall clock (66% in one overnight coding run); overlapping them with model work is the emerging fix.
---

## TL;DR
A chatbot waits on one model call; an agent waits on *many*, in sequence:
plan, call a tool, read the result, decide again. The wall-clock a user feels
is per-step latency multiplied by loop length, so a serving stack tuned for
single-shot throughput can still leave an agent slow. Latency is the run-time
twin of [cost](/topic/agent-cost): the loop that runs up the bill also runs
out the clock.

## State of the art
Agent latency is attacked at several layers at once, and in long agent runs
the binding constraint is often outside the model entirely.

**Agent traffic is not chat.** Coding agents send bursty, long-context,
tool-interleaved requests with over 80% KV-cache reuse. Schedulers are being
rebuilt for that shape: session-aware scheduling, routing inside the serving
layer, co-scheduling inference with tool environments (10-65% faster batch
completion), and systems that retune themselves online to live traffic.

**The bottleneck is moving KV state, not FLOPs.** The context grows every
step, and streaming it back is bandwidth-bound. Four answers compete:
compress the cache (now losslessly, at 0.71x size), offload it to shared RAM
and NVMe tiers (AMD reports NVMe within 1% of DRAM throughput), shard it
across GPUs, or reuse it through prefix-aware routing. Reuse has a sharp
edge: once reused text sits mid-prompt, an unrepaired cache can score worse
than none.

**Engines are specializing, and tuning is measured.** Disaggregation splits
serving by phase and by compute type. New models get tuned serving on day 0,
then per-release kernel gains of a few percent per token. Measured config
search beat expert vLLM settings by 1.5-2.3x, with a different winner per
model, so defaults are a starting point, not an answer.

**Doing less work per step** is the other lever: small latency-first models,
learned prompt compression, sparse attention, and better speculative
drafting. Context trimming has a measured cliff: below half the budget,
failure odds rise sharply unless trimming preserves instructions and tool
state.

**The open problem sits outside the engine.** One overnight coding run spent
66% of wall clock on UI tests and simulator checks and 26% on the model. Tool
round-trips, verification, and cold starts dominate such loops, and no
serving optimization touches them. Overlapping that work (running tools while
the user speaks, watching the screen with a small monitor) is where the next
gains are. Voice sets a hard floor the whole loop must meet.

## Why it matters for platform engineers
Latency is where the agent's architecture meets the user's patience and the
GPU bill, and the three trade against each other directly.

Budget latency across the *whole loop*, not per call: count the sequential
model hops, push what you can to a faster or smaller model, and cut the tokens
decoded and streamed each step ([compaction](/topic/context-compaction), KV
reuse, [speculative decoding](/topic/speculative-decoding)). Pick a serving
engine tuned to the bursty, long-context shape agents produce, not a chat
benchmark. Measure tool latency cold, not against a warm cache.

Interactive modes (voice, live coding) set a hard ceiling, so the deliverable
is a latency budget you can reason about per task, not a one-time inference
optimization.
