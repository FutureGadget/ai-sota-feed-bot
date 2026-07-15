---
slug: agent-cost
kind: obstacle
title: "Agent token costs are unpredictable and easily run away"
area: cost
status: active
solutions: [cost-controls, context-compaction, agent-orchestration]
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, 9ff56fe893f2ff23, d950eaa58be54c93, c8dc1df614610019, 4a0a79e7203bae64, c74bb13bcd038d10, 68e97756211ddc61, 4f6620afcff4153a]
updated: 2026-07-15
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, 9ff56fe893f2ff23, d950eaa58be54c93, c8dc1df614610019, 4a0a79e7203bae64, c74bb13bcd038d10, 68e97756211ddc61, 4f6620afcff4153a]
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
than peak chip specs, with hard numbers behind the pitch: NVIDIA reports its
GB300 NVL72 rack delivering 10-25x the performance-per-watt of the prior
Hopper generation across three current open models, a further 5x
software-only gain on one of them within a single month (quantization,
disaggregated serving, KV-cache offloading, no new hardware), and power-shifting
software that lets an operator run up to 40% more GPUs inside the same power
budget — a reminder that for self-hosted agents the inference stack sets the
floor price every other optimization multiplies against.

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

**Fetched content is its own cost line**, and it's now measured directly: one
practitioner clocked an average Wikipedia article at 68,240 raw-HTML tokens
against a 950-token summary once a web-fetch tool condenses it — and found
the cheap path can invert on JS-rendered or anti-bot-protected pages, where
the fetch returns nothing useful and the agent dumps the full raw HTML back
into context anyway, paying the worst-case token bill for a failed read.

The flip side of that knob is the biggest single lever: **spending context
to downshift the model**. Cheap models are far cheaper per token but ignore
architecture rules — ANMA reports Claude Haiku 4.5 violating its constraints
in 13 of 19 runs unguided, but 0 of 20 once wrapped in explicit boundary
contracts (YAML rules plus `CLAUDE.md`, hooks, and CI checks) — so a bit of
contract overhead can make a cheaper model reliable enough to replace a
frontier one on the bulk of the work.

A second case makes the same point with a harder cost number attached:
LangChain retuned only the harness — prompts, tool schemas, control flow —
around NVIDIA's Nemotron 3 Ultra and matched Claude Opus 4.8's best agent
run at roughly 8x lower cost, without fine-tuning the model or swapping in a
bigger one. Scaffolding investment pays off on every call a harness handles;
buying a bigger model buys quality once, per call.

A third report puts the same cost/reliability exchange on a frontier-adjacent
model swap rather than harness tuning or contract engineering: coverage of
Grok 4.5 puts the coding-agent cost cut at roughly 80% versus a comparable
frontier setup, at near-frontier speed, but with a higher hallucination
rate — the same trade the Haiku and Nemotron cases above make explicit with
boundary contracts and harness tuning, here left unmitigated.

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

**Test-time-scaling cost** is a related but distinct lever from the model
downshift above: generating many parallel attempts per problem to improve
answer quality is a reliable but expensive pattern, and by default those
attempts are independent, wasting inference budget on redundant samples.
QuasiMoTTo applies quasi-Monte Carlo sampling to spread parallel attempts
more evenly across the solution space instead of drawing them independently,
cutting the redundancy tax on a pattern (parallel sampling) that agent
harnesses increasingly reach for when a single pass isn't reliable enough.

**Tool-calling behavior**, not just model choice, is now a cost lever in its
own right: when GitHub retuned Copilot code review onto shared Unix-style
tools (`grep`/`glob`/`view`), average cost went *up* at first, because the
new tools' instructions invited broad, exploratory browsing suited to an
interactive coding assistant rather than the narrow, diff-anchored search a
reviewer actually needs. Rewriting the tool instructions — not the tools
themselves — to start from the diff, batch searches before reading, and read
only the needed line ranges cut average review cost roughly 20% while
holding review quality, evidence that a tool's *instructions* are as much a
cost surface as the tool's schema. Judge cost gets the same treatment as
agent cost: mining production traces for failure clusters and fine-tuning a
small judge on them, rather than running a frontier model as the judge,
is the same cheap-instrumentation-over-model-swap move already established
for [evaluation](/topic/agent-evaluation).

## What's new
The "cost per watt" framing on the infra-level lever now has hard numbers
behind it instead of a generic vendor pitch: NVIDIA's GB300 NVL72 reports
10-25x the performance-per-watt of the prior Hopper generation, plus a
further 5x software-only gain in a single month and up to 40% more GPUs
runnable inside the same power budget — evidence that for self-hosted agents
the serving stack itself, not just model choice, moves the cost floor.

## Why it matters for platform engineers
This is the obstacle that turns a working demo into an unaffordable product.

The job is to make spend observable per task and per user, set budgets and
caps before a loop runs away, and treat the architecture (compact vs.
retrieve, single-agent vs. orchestrated, frontier vs. fine-tuned judge) as
the primary cost control — because the biggest savings come from *how* the
agent is built, not from shaving the model price.

Cost, latency, and reliability trade against each other, so the deliverable
is a cost model you can reason about, not a one-time optimization.
