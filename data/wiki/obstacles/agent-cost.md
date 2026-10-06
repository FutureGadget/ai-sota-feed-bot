---
slug: agent-cost
kind: obstacle
title: "Agent token costs are unpredictable and easily run away"
area: cost
status: active
solutions: [cost-controls, context-compaction, agent-orchestration]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: harness-and-context
    title: Harness, context, and topology drive the per-step bill
    summary: What the agent re-reads, fetches, and re-sends each turn sets most of the bill; validated compaction, tool-instruction tuning, and task-level measurement beat naive truncation.
  - key: cheaper-models
    title: Downshifting to cheaper models, costed on total tokens
    summary: Contracts and harness tuning let cheaper models take frontier work at 5-8x lower cost, but quantization and hallucinations can claw the discount back in extra tokens.
  - key: routing
    title: Routing each turn to the cheapest model that can handle it
    summary: Benchmarks find most agent turns don't need a frontier model; per-thread routing inside the harness cuts cost 64-74%, and online tuning of the routing policy is emerging.
  - key: caching-and-serving
    title: Caching and serving efficiency set the floor price
    summary: Prompt caching at 90%+ hit rates, KV-cache offload, GPU packing, and pay-for-use runtimes cut fixed cost by large factors before any model choice.
  - key: price-curve
    title: Falling token prices, rising workflow spend
    summary: Frontier and open-weight per-token prices fall together and open weights now win gateway traffic, yet spend per agentic workflow is forecast to keep climbing.
---

## TL;DR
A chatbot turn costs a predictable number of tokens; an agent can loop, re-read
its whole context every step, spawn sub-agents, and call a model to grade its
own work. The bill is a function of *behavior*, not request count, so one
misbehaving run or one topology choice can multiply spend before anyone sees
the invoice.

## State of the art
**Per-token prices are falling, but per-task spend is not.** Frontier and
open-weight prices drop together, yet Gartner forecasts cost per agentic
workflow rising more than fivefold through 2028, because spend scales with
steps and tool calls. The deliverable is a cost model per task, not a price
list.

Teams pull four levers, roughly in order of payoff:

- **Cache the stable prefix.** An agent re-sends its system prompt, tool
  schemas, and history every turn. Production setups report 90-99% cache
  hits, and Anthropic's worked example shows one session at $11.20 uncached
  versus $1.62 cached.
- **Route per task.** Benchmarks find only about 7% of agent turns need a
  frontier model; routing inside the harness cut cost 64-74%.
- **Shrink what the agent re-reads.** Validated compaction, tighter tool
  instructions, and leaner fetched content attack the per-step bill. Naive
  truncation backfires: agents re-fetch what was cut.
- **Downshift with guardrails.** Boundary contracts and harness tuning let
  cheap models match frontier runs at several times lower cost.

**Cost every downshift on total tokens, not sticker price.** Quantized
reasoning models emit more tokens, cheaper models hallucinate more, and
truncation triggers retries. Each can erase the discount. Billing data
backs the routing case: a weeks-old frontier model took 3.5% of one vendor's
spend.

**The open problem is accounting at the right unit.** Most reported savings
are vendor-measured, offline, or single-customer. Mid-thread re-routing is
unsolved, and runaway spend remains the default without an enforced cap
(see [cost controls](/topic/cost-controls)). Self-hosters face a parallel
floor: GPU utilization, KV-cache placement, and runtime billing often matter
more than list price.

## Why it matters for platform engineers
This is the obstacle that turns a working demo into an unaffordable product.

Make spend observable per task and per user, and set budgets and caps before
a loop runs away. Then treat architecture as the main cost control: compact
vs. retrieve, single-agent vs. orchestrated, frontier vs. routed or
fine-tuned models. The biggest savings come from *how* the agent is built,
not from shaving the model price.

Cost, latency, and reliability trade against each other, so the deliverable
is a cost model you re-run on each model release, not a one-time
optimization. See [context compaction](/topic/context-compaction) and
[orchestration](/topic/agent-orchestration).
