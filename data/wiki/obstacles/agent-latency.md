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
updated: 2026-10-06
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
    summary: Tool round-trips (search APIs, data queries, CI) and cold starts often dominate the loop, and voice sets a hard floor the whole stack must meet.
---

## TL;DR
A chatbot waits on one model call; an agent waits on *many*, in sequence:
plan, call a tool, read the result, decide again. The wall-clock a user feels
is per-step latency multiplied by loop length, so a serving stack tuned for
single-shot throughput can still leave an agent slow. Latency is the run-time
twin of [cost](/topic/agent-cost): the loop that runs up the bill also runs
out the clock.

## State of the art
Agent latency is attacked at several layers at once, and the binding
constraint has moved from compute to memory.

**Agent traffic is not chat.** Coding agents send bursty, long-context,
tool-interleaved requests with over 80% KV-cache reuse. Schedulers, batchers,
and routers are being rebuilt for that shape: session-aware scheduling,
learned batching policies, and routing logic pulled inside the serving layer.
vLLM's AgentX tuning shows these levers compound when tuned together, though
its cost comparison is vendor-reported.

**The bottleneck is moving KV state, not FLOPs.** The context grows every
step, and streaming it back is bandwidth-bound. Four answers compete: compress
the cache, offload it to shared RAM/NVMe tiers, shard it across GPUs, or reuse
it through prefix caching, prefix-aware routing, and cross-model KV transfer.
Reuse has a sharp edge: once reused text sits mid-prompt, as in RAG and
multi-agent handoffs, an unrepaired cache can score worse than none.

**Engines are specializing.** Disaggregation now splits by phase
(prefill/decode) and by compute type (attention/FFN). New open-weight models
and accelerators get tuned serving on day 0, then steady per-release kernel
gains of a few percent per token, which multiply across every step of a loop.

**Doing less work per step** is the other lever: small latency-first models
for the bulk of calls, learned prompt compression (Shopify cut end-to-end
latency from 6.8s to 4.2s), and better speculative drafting. Context trimming
has a measured cliff: below half the budget, failure odds rise sharply unless
trimming preserves instructions and tool state.

**The open problem sits outside the engine.** Tool round-trips (search APIs
with a 12x latency spread and short-lived caches, fan-out data queries, remote
CI) and cold starts often dominate wall-clock time, and no serving
optimization touches them. Voice sets a hard floor the whole loop must meet.

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
