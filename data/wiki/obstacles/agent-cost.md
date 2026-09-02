---
slug: agent-cost
kind: obstacle
title: "Agent token costs are unpredictable and easily run away"
area: cost
status: active
solutions: [cost-controls, context-compaction, agent-orchestration]
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, 9ff56fe893f2ff23, d950eaa58be54c93, c8dc1df614610019, 4a0a79e7203bae64, c74bb13bcd038d10, 68e97756211ddc61, 4f6620afcff4153a, 1e95bee9c26709cb, 44423c0a85b4d691, b3d901fa5502f189, fae52c3b17c1c504, 483f6bab97830d53, 309c04c4364dddf7, 7f18e7dd55749326, 053f960947801f33, d9ba824f19c5d4d4, bef171cfa1a2b219, 22188ce2d79de3bb, 682443ee05b543bd, fcb5eeae253e1eba, 26b283e0296ba33f, 67eb8445f6de26d6, c26d5834adc52fbd, 530f8771d0d2a226, b6461cff58b0d468, 2d5ee61a05111f0a, 5a94dd163bfbe84d, afd300f326ca249d, cd7265fbc46b3ca2, 5f95a73de65c4e0a, bb8327f0dd55b3b1, 5b17581a4141c149, 0577669e18ed3998, 31d0f6b1d6dddfa7, 40944f4dff2445be]
updated: 2026-09-02
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d, c4fa725d5c123b2d, edd85739d7d91365, b4e45006617c01bc, 7b1828a20dc37818, 5bd881e763537559, 9ff56fe893f2ff23, d950eaa58be54c93, c8dc1df614610019, 4a0a79e7203bae64, c74bb13bcd038d10, 68e97756211ddc61, 4f6620afcff4153a, 1e95bee9c26709cb, 44423c0a85b4d691, b3d901fa5502f189, fae52c3b17c1c504, 483f6bab97830d53, 309c04c4364dddf7, 7f18e7dd55749326, 053f960947801f33, d9ba824f19c5d4d4, bef171cfa1a2b219, 22188ce2d79de3bb, 682443ee05b543bd, fcb5eeae253e1eba, 26b283e0296ba33f, 67eb8445f6de26d6, c26d5834adc52fbd, 530f8771d0d2a226, b6461cff58b0d468, 2d5ee61a05111f0a, 5a94dd163bfbe84d, afd300f326ca249d, cd7265fbc46b3ca2, 5f95a73de65c4e0a, bb8327f0dd55b3b1, 5b17581a4141c149, 0577669e18ed3998, 31d0f6b1d6dddfa7, 40944f4dff2445be]
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
attacks the per-step token bill directly — naive context accumulation grows
that bill quadratically in conversation length, crude summarization buys
linear cost at the price of an accuracy cliff, and only validated compaction
achieves linear cost with fidelity preserved, per "Agentic Context
Management" (ACM)'s framing and its reference implementation, Maximem Synap;
choosing a cheaper [orchestration](/topic/agent-orchestration) topology
matters because the coordination structure dominates spend — Stanford's DeLM
reports cutting multi-agent task cost ~50% by dropping the central
orchestrator; and even evaluation is a cost line item, which is why teams
fine-tune small judges to cut trace-judging cost ~100×.

**The routing layer itself is becoming a build-vs-buy cost decision**: as
hosted LLM routers proliferate (Ramp Router, Vercel's AI Gateway) and
OpenRouter faces a possible acquisition, Millwright — a self-hosted,
Rust-based LLM router — reframes routing as infrastructure a team owns for
cost savings and transparency, rather than a hosted layer with vendor
consolidation and lock-in risk baked in (see [cost
controls](/topic/cost-controls) for the concrete instance). Routing is also
getting a formal treatment as an allocation problem rather than a heuristic:
"Pandora's AI Model Routing Box" frames choosing among heterogeneous models
and harnesses as efficient allocation under a costly-to-estimate value
signal, and Glean's CEO makes the buyer-side case for the same shift —
frontier price and open-weight uptake are both pushing organizations toward
routing, with feedback loops at scale improving the router's decisions over
time. The runaway-spend failure mode this page's TL;DR describes is still
the default without an enforced ceiling: an open-source terminal research
agent (Mole) documents its own motivation as agents that "blow way past
budget, jumble the sources, and don't even give you the best possible
answer" — told from the tool builder's side rather than a vendor's
mitigation (see [cost controls](/topic/cost-controls) for the concrete
per-call spend-enforcement answer, AgentCore Payments).

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
floor price every other optimization multiplies against. A production case
study puts a number on the utilization side of that floor price: Heidi
Health found individual ASR inference requests using only 15-20% of an
NVIDIA L40S's streaming multiprocessors, with the rest sitting idle each
forward pass — packing 4-8 concurrent requests onto one GPU via CUDA's
Multi-Process Service instead of dedicating a GPU per request cut the GPU
count needed for the same throughput by 75%, from 16 instances down to 4.

The **sandboxing layer doubles as a cost lever**, not just a security
control: Google's GKE Agent Sandbox reports cutting cost per agent by
roughly 75% for platform teams running many concurrent agent workloads —
tying [sandboxing](/topic/agent-sandboxing)'s isolation choice directly to
this page's cost line rather than only to blast-radius containment.

**Caching** cuts fixed cost at every layer: container/image caching (Amazon
SageMaker) cuts cold-start scaling cost and latency; prompt caching the
agent loop's stable prefix is becoming a framework default (LangChain's Deep
Agents reports up to ~80% token-cost cuts across providers with no config),
since an agent re-sends its system prompt, tool schemas, and prior steps
every turn; and inside the model, KV-cache reuse cuts a cost specific to
multimodal agents that re-read the same frames or screenshots each step —
Kamera's position-invariant cache reuses those visual tokens across context
shifts instead of re-encoding them every look-back. Compaction is starting to
treat images as a first-class part of the token budget too: Codex's remote
compaction now counts retained images against its budget by default and
trims the oldest ones as needed, instead of letting accumulated screenshots
silently inflate the context it has to re-send every turn. **KV-cache offload is
becoming its own storage-engineering problem**: OpenLake moves the cache
from GPU memory into a shared RAM/NVMe tier and compresses blocks losslessly
before they leave the GPU, so a prefix cached on one host is cheap to fetch
from another instead of being recomputed — on a 128K-context workload this
cut total GPU time from 1,169 to 606 seconds, a 48.2% GPU-cost reduction.
A parallelism-based answer attacks the same long-context bottleneck from a
different angle: vLLM's Decode Context Parallelism shards the KV cache
across GPUs by sequence dimension instead of offloading it, reporting 3x
higher decode throughput on long-context agentic workloads versus standard
tensor parallelism — more throughput per GPU-hour on the same hardware is a
direct cost lever, not just a latency one (see [agent
latency](/topic/agent-latency) for the full serving-stack detail).

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

A fourth lever trades data rights for price rather than model size or
reasoning effort: Meta's Muse Code Mac coding agent cuts subscription cost
up to 20x for users who opt into letting the agent train on their code and
usage data — the same downshift logic as the model-size and
reasoning-effort levers above, but the currency paid is data access rather
than accuracy or latency.

**Test-time-scaling cost** is a related but distinct lever from the model
downshift above: generating many parallel attempts per problem to improve
answer quality is a reliable but expensive pattern, and by default those
attempts are independent, wasting inference budget on redundant samples.
QuasiMoTTo applies quasi-Monte Carlo sampling to spread parallel attempts
more evenly across the solution space instead of drawing them independently,
cutting the redundancy tax on a pattern (parallel sampling) that agent
harnesses increasingly reach for when a single pass isn't reliable enough.

**Reasoning effort itself is becoming a trainable, explicit dial** rather than
a fixed per-model setting. Models increasingly expose low/medium/high
reasoning-effort modes through several mechanisms — system-prompt
conditioning that tells the model how hard to think, RL training with
per-token cost coefficients that reward shorter traces at low effort and
allow longer ones at high effort, SFT that mixes thinking and non-thinking
examples, or distilling several separately-trained reasoning-depth
specialists into one model. Token consumption swings roughly 25-50% across
effort levels, and a smaller model at high effort can match a larger model at
low effort — so model size and reasoning effort have to be tuned jointly, not
model size alone. For an agent harness this turns reasoning effort into a
routing decision: effort should be selected per request, based on task
complexity and how much verification the step needs, rather than fixed once
for the whole agent.

A benchmarked routing result puts a hard number on that per-request decision:
NVIDIA's NeMo Switchyard, run across 145 agent tasks, found only 7% of turns
actually needed a frontier model — routing the rest to cheaper models cut
total cost 74% for a six-point accuracy trade-off. It's direct evidence that
most of an agent's turn-by-turn cost is spent on calls that didn't need
frontier capability in the first place, sharpening the reasoning-effort-as-
routing-decision argument above into a measured split rather than a
qualitative one.

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

**Harness-side cost bugs are their own line item**, distinct from model or
architecture choice: Claude Code v2.1.216 fixed a slowdown where long-session
message normalization cost grew *quadratically* with the number of turns,
causing multi-second stalls and slow resumes — a reminder that the harness's
own bookkeeping, not just the model calls it makes, can be the thing that
turns a long-running agent session expensive and slow. The same release
also split filesystem isolation from network egress control as independent
sandbox settings (see [sandboxing](/topic/agent-sandboxing)), letting a team
tune the security/cost trade-off of each control separately instead of
paying for both whenever either is needed. A later release turned that same
bookkeeping toward accuracy rather than speed: v2.1.239 folds the 1.1x
US-only-inference premium that data-residency workspaces pay into the cost
estimates `/cost`, the status line, and `--max-budget-usd` actually show, so
a team on a residency-locked workspace sees its real regional cost instead
of the base rate.

**Falling code-generation cost is reshaping the ROI calculation itself**, not
just the per-call bill: coding agents have made reverse-engineering
undocumented home-device APIs cheap enough that the traditional "is it worth
the maintenance risk" calculus barely applies — when writing the automation
is nearly free, so is throwing it away and rewriting it if the undocumented
API changes, which removes the psychological cost that used to gate the
work. It's the same cost/ROI reframing [proving agent
ROI](/topic/proving-agent-roi) tracks from the enterprise side, showing up
here as a change in what individuals bother to build at all.

**The frontier price war just got sharper on both ends at once**: GPT-5.6
cut list price 20-80%, with the cost of GPT-5.4-level intelligence reported
down roughly 13x in four months via recursive self-optimization (using the
model to distill and improve its own successor), while China's open-weight
labs keep pushing the same curve down from the other side — DeepSeek shipped
another cheaper model as the domestic price war intensifies, and
AMD's MI355X now undercuts Nvidia's B300 on cost-per-token to run China's
Kimi K3. The frontier and open-weight price curves are falling together, not
one converging toward the other. DeepSeek's V4 Flash sharpens that open-weight
side with a specific number: running a full test suite at $72 against Kimi
K3 on the same job, a roughly 33x gap — evidence the domestic price war isn't
just cutting list price, it's compounding the gap between individual
open-weight releases too.

That price pressure now shows up in where the traffic actually goes, not
just in list prices: open-weight models overtook proprietary ones on
Vercel's AI Gateway for the first time, taking 54% of token volume on one
day and a record 62% on another, up from just 28% on June 24 — with
DeepSeek-V4-Flash the single most-used model by volume and Chinese models
filling out the rest of the top five (StepFun's Step 3.7 Flash, Zhipu's
GLM-5.2). The next wave of releases keeps widening that gap on cost rather
than capability: Zhipu's GLM-5.3-Flash lands within three points of its own
larger GLM-5.3 on Artificial Analysis's Intelligence Index at roughly a
seventh of the cost, with all inference running on Chinese chips instead of
Nvidia hardware, and Alibaba's Qwen3.8-Flash-Next prices in at $0.16/$0.47
per million input/output tokens — about a twelfth of Qwen3.8-Max's cost and
a ninth of Qwen3.7-Plus's training cost — while beating Claude Opus 4.6 on
SWE-bench Pro (62.5 vs. 53.4).

Zooming out, the aggregate trend is still climbing even as every lever above
pushes down: Gartner forecasts inference cost per agentic *workflow* will
increase more than fivefold through 2028, because workflow spend scales with
the number of steps and tool calls an agent takes, not with the price of any
single token — the same reason a falling per-token price, frontier or
open-weight, doesn't guarantee a falling bill once workflows get more
agentic, not just cheaper per call.

**Real billing data shows where that spend actually lands, and it isn't the
frontier model.** A breakdown of Anthropic's own July spend by model (the
Ramp AI Index, built from 70,000 companies' credit-card billing data) shows
Opus 5 — the newest, most capable model, released weeks earlier — capturing
only 3.5% of spend, while the prior-generation Opus 4.8 still takes 28%.
Anthropic's annualized revenue climbed to $65bn in the same period, up from
$47bn two months earlier, so the spend itself is real and growing; it just
isn't concentrating on the frontier model, evidence for the routing and
reasoning-effort arguments above that most per-task spend doesn't need
frontier capability.

A second production case study puts an even higher number on the same
caching lever, plus the discipline that gets there: Anthropic's own
commerce-agents guide reports 90-99% prompt-cache hit rates in production,
achieved by keeping a byte-identical prefix across three cache segments —
global (rarely changes), session (stable for the conversation), and volatile
(changes every turn) — so only the volatile segment actually breaks the
cache each turn, with cached tokens reading back 1.5-2x faster than an
uncached read. The same guide's latency playbook targets three separate
levers rather than one: fewer turns (pre-loaded context, parallel tool
calls), faster tools (backend optimization, dispatching a tool call's
arguments as they stream instead of waiting for the full response before
acting), and faster tokens (model selection driven by eval sweeps over real
traffic, not a leaderboard score). It pairs the cost playbook with a
safety-in-code discipline that keeps spend-relevant actions off the model's
say-so alone: no financial action executes without staging and human
approval, writes accept only server-issued IDs rather than a model-typed
one, and transaction caps enforce a ceiling on the resulting state instead
of the request.

## What's new
Anthropic's own commerce-agents guide reports 90-99% prompt-cache hit rates
in production via a byte-identical three-segment cache (global/session/
volatile), cached tokens reading 1.5-2x faster than uncached ones, alongside
a code-not-prompt safety discipline: staged approval before any financial
action, server-issued IDs on writes, and transaction caps enforced on
resulting state (see State of the art above).

Prior update: Open-weight models overtook proprietary ones on Vercel's AI Gateway for the
first time — 54% of token volume on one day, a record 62% on another, up
from 28% on June 24 — with DeepSeek-V4-Flash the single most-used model by
volume, while the next wave of Chinese releases (Zhipu's GLM-5.3-Flash,
Alibaba's Qwen3.8-Flash-Next) widens the cost gap further still: within
three points of larger siblings on quality benchmarks at a seventh to a
twelfth of the cost (see State of the art above).

Prior update: A breakdown of Anthropic's own July spend by model shows the newest,
most-capable model (Opus 5) capturing only 3.5% of spend versus 28% for the
prior-generation Opus 4.8, even as Anthropic's annualized revenue grew to
$65bn — real billing evidence that most agent spend goes to a model that
already clears the bar, not the frontier one (see State of the art above).

Prior update: Model routing gets a formal allocation-theory treatment ("Pandora's AI Model
Routing Box") and a buyer-side business case (Glean's CEO) in the same
window, both arguing frontier price and open-weight uptake are pushing
organizations toward routing as infrastructure rather than a one-off
optimization (see State of the art above).

## Why it matters for platform engineers
This is the obstacle that turns a working demo into an unaffordable product.

The job is to make spend observable per task and per user, set budgets and
caps before a loop runs away, and treat the architecture (compact vs.
retrieve, single-agent vs. orchestrated, frontier vs. fine-tuned judge) as
the primary cost control — because the biggest savings come from *how* the
agent is built, not from shaving the model price.

Cost, latency, and reliability trade against each other, so the deliverable
is a cost model you can reason about, not a one-time optimization.
