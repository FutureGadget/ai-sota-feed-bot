---
slug: agent-cost
kind: obstacle
title: "Agent token costs are unpredictable and easily run away"
area: cost
status: active
solutions: [cost-controls, context-compaction, agent-orchestration]
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, c0c3ec4a6aba7980]
updated: 2026-07-02
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, c0c3ec4a6aba7980]
---

## TL;DR
A chatbot turn costs a predictable number of tokens; an agent can loop, re-read
its whole context every step, spawn sub-agents, and call a model to grade its
own work — so the bill is a function of *behavior*, not request count, and a
single misbehaving run or a topology choice can multiply spend without anyone
noticing until the invoice arrives. Cost is the run-time obstacle that the
build-time decisions (memory, multi-agent, eval) silently determine.

## State of the art
Cost is being attacked on two fronts: **making it visible** and **making it
smaller**.

Visibility is moving from a monthly surprise to a first-class signal —
enterprise platforms now ship usage analytics and hard spend controls
(OpenAI's enterprise spend caps), and developer tooling attributes cost down
to the unit of work, e.g. showing how many agent tokens a single pull
request consumed (Prtokens). Visibility is even being automated *as an
agent*: AWS's FinOps Agent (public preview) investigates cost anomalies and
correlates spend changes with account activity, turning the after-the-fact
bill review into a continuous, queryable analysis — cost analysis is itself
becoming an agentic product.

The **reduction side** is the sum of the other obstacles' solutions: keeping
the working set small via [context compaction](/topic/context-compaction)
attacks the per-step token bill directly (the cost scales with context
size); choosing a cheaper [orchestration](/topic/agent-orchestration)
topology matters because the coordination structure dominates spend —
Stanford's DeLM reports cutting multi-agent task cost ~50% by dropping the
central orchestrator; and even evaluation is a cost line item, which is why
teams fine-tune small judges to cut trace-judging cost ~100×.

**Infra-level levers** help too, and the serving stack is increasingly
pitched as a cost lever in its own right: vendors now frame the buying
decision as cost per useful token — tokens per dollar and per watt — rather
than peak chip specs (NVIDIA's inference-software writeup), a reminder that
for self-hosted agents the inference stack sets the floor price every other
optimization multiplies against.

**Caching** cuts fixed cost at every layer: container/image caching (Amazon
SageMaker) cuts cold-start scaling cost and latency; prompt caching the
agent loop's stable prefix is becoming a framework default (LangChain's Deep
Agents reports up to ~80% token-cost cuts across providers with no config),
since an agent re-sends its system prompt, tool schemas, and prior steps
every turn; and inside the model, KV-cache reuse cuts a cost specific to
multimodal agents that re-read the same frames or screenshots each step —
Kamera's position-invariant cache reuses those visual tokens across context
shifts instead of re-encoding them every look-back.

A subtler driver is the **context cost of instructions themselves** — every
skill, hook, or subagent you add to steer an agent consumes context budget,
so steering and cost are the same knob viewed from two sides.

The flip side of that knob is the biggest single lever: **spending context
to downshift the model**. Cheap models are far cheaper per token but ignore
architecture rules — ANMA reports Claude Haiku 4.5 violating its constraints
in 13 of 19 runs unguided, but 0 of 20 once wrapped in explicit boundary
contracts (YAML rules plus `CLAUDE.md`, hooks, and CI checks) — so a bit of
contract overhead can make a cheaper model reliable enough to replace a
frontier one on the bulk of the work.

The cheaper-model lever has a hidden counterweight, though: **a lower
per-token price can be eaten by a higher token count**. "Quantization
Inflates Reasoning" shows that low-bit post-training quantization — the
standard way to cut inference cost — makes reasoning models emit *more*
tokens to reach the same answer, so final-answer accuracy and per-token
latency both miss the real bill; the cost that matters for an agent is
price-per-token times the tokens the run actually spends, and a quantized
model can claw back its discount in inflated reasoning traces.

The lesson generalizes: every downshift (smaller model, quantized model,
cheaper judge) has to be costed on *total tokens emitted in the loop*, not
the sticker price per token.

**Test-time compute efficiency** is emerging as its own lever, distinct
from model downshift: QuasiMoTTo replaces independent random sampling in
parallel-attempt scaling with quasi-Monte Carlo sampling, covering the
solution space more evenly so fewer parallel attempts are needed to reach
the same accuracy — the same "total tokens spent, not sticker price"
accounting the quantization caution above already argues for. A second
lever restructures calls *inside* one model API instead of downshifting to
a smaller one: vLLM's Semantic Router turns routing itself into a bounded
"micro-agent" runtime — confidence-based escalation, capped rating
ensembles, and fusion across a small panel of calls — that reportedly beats
frontier single-call performance through that bounded collaboration, not
because the calls themselves are cheaper.

## What's new
Two new levers target the *how many calls* side of cost rather than the
per-token price: QuasiMoTTo swaps random sampling for quasi-Monte Carlo
coverage in parallel-attempt scaling so fewer samples reach the same
accuracy, and vLLM's Semantic Router restructures calls inside one model
API — confidence escalation, rating, fusion across a small panel — to beat
frontier single-call performance through bounded collaboration rather than
per-call cost. Both extend the "cost is total tokens spent, not price per
token" accounting already established by the quantization caution.

Cost is becoming an explicit, **measured surface** rather than an
after-the-fact invoice: enterprise spend caps and usage analytics, per-PR
token-cost attribution (Prtokens), and now-managed agentic cost analysis
(AWS FinOps Agent investigates anomalies and correlates spend with
activity).

There's a growing recognition that the **cheapest lever is architectural**:
decentralized topologies (DeLM, ~50% off), cheap fine-tuned judges (~100×
off), and contract layers that make a cheaper model obey rules well enough
to downshift to it (ANMA: Haiku rule-violations 13/19 → 0/20) rather than a
smaller model alone.

A **caution** lands on the model-downshift lever: "Quantization Inflates
Reasoning" finds that low-bit quantization cuts per-token cost but inflates
the token count reasoning models emit, so the saving is partly illusory
unless you cost the run on total tokens spent rather than the per-token
price.

For self-hosted stacks the **floor price is itself moving**: vendors now
frame inference as cost per useful token (per dollar and per watt) rather
than peak chip specs (NVIDIA), making the serving stack a cost lever every
other optimization multiplies against.

## Why it matters for platform engineers
This is the obstacle that turns a working demo into an unaffordable product.

The job is to make spend observable per task and per user, set budgets and
caps before a loop runs away, and treat the architecture (compact vs.
retrieve, single-agent vs. orchestrated, frontier vs. fine-tuned judge) as
the primary cost control — because the biggest savings come from *how* the
agent is built, not from shaving the model price.

Cost, latency, and reliability trade against each other, so the deliverable
is a cost model you can reason about, not a one-time optimization.
