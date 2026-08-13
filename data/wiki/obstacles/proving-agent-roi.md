---
slug: proving-agent-roi
kind: obstacle
title: "Proving agent ROI and measuring cost efficiency is hard"
area: cost
status: active
solutions: [cost-controls, llm-as-judge]
obstacles: []
related_storylines: []
evidence: [c4fa725d5c123b2d, 00f3793762a13f49, 4a5901ff818ec6d5, 769505c4770ec3dc, 4235792e910ea51a, 19e4caf222bfb0d9, a495552f9c306031, 055894614946248f, c5c5248230951857, 069dd5549b1700c4, 26b283e0296ba33f]
updated: 2026-08-13
covers_evidence: [c4fa725d5c123b2d, 00f3793762a13f49, 4a5901ff818ec6d5, 769505c4770ec3dc, 4235792e910ea51a, 19e4caf222bfb0d9, a495552f9c306031, 055894614946248f, c5c5248230951857, 069dd5549b1700c4, 26b283e0296ba33f]
---

## TL;DR
Calculating the true return on investment (ROI) for agent systems is blocked by the difficulty of measuring time-savings, tracking per-task token usage, and accounting for hidden costs like token inflation in low-bit quantized models. Platform engineers must transition from generic productivity claims to precise, instrumented cost-per-task accounting and evidence-based time-savings measurement.

## State of the art
Proving that an agent is cost-efficient requires attributing model spend and execution latency directly to the business outcome it delivers, rather than looking at aggregate API usage.

**Attribution and Metering:**
Tools like AgentMeter and Prtokens enable developers to attribute token costs down to the individual unit of work, such as a pull request or a user session. This granular data is necessary to prove whether an agent's cost is justified by the task outcome. Local guardrail packages (like ai-costguard) enforce hard cost budgets directly in the runtime loop, preventing runaway agents from consuming resources. Model vendors are shipping the admin side of the same job: Claude Enterprise's new usage analytics add model-level entitlements and spend alerts on top of adoption tracking, so an org can attribute and cap spend centrally instead of every team building its own metering. AWS's self-hosted Claude apps gateway extends that same governance job past a single vendor's own console — a control plane an org runs itself, giving central access, cost, and policy control over Claude Code and Claude Desktop usage on Bedrock rather than relying on Anthropic's own admin surface.

**Hidden Costs of Optimization:**
Teams frequently downshift from frontier models to smaller or quantized models to improve cost efficiency, but this optimization has a hidden cost. Low-bit post-training quantization is widely used to reduce model size, but it degrades reasoning capability. Research shows that quantized reasoning models (like "Quantization Inflates Reasoning") emit *more* tokens to arrive at the same answer, meaning the per-token price discount is partially offset by token inflation. True ROI analysis must measure the total tokens spent per task run, not just the per-token model rate.

**Cost-Sensitive Topologies:**
Decentralizing agent orchestrations also dramatically cuts task execution spend. Stanford's DeLM demonstrates that removing the central orchestrator from multi-agent structures cuts task costs by up to 50% while maintaining target completion rates, shifting the optimization focus from model choosing to topology design. Similarly, using cheaper fine-tuned open models (like Fireworks trace judges) to evaluate production runs cuts trace-evaluation costs by 100x compared to frontier judges.

**Naming the metric itself:**
The ROI conversation is also converging on which numbers to track: OpenAI's
own CFO has proposed a practical AI scorecard built on useful work delivered,
cost per successful task, dependability, and return on compute — the same
per-task attribution this page argues for, but pushed by a finance function
rather than an engineering team, evidence the cost-per-task framing is
becoming the standard ROI vocabulary rather than one platform-engineering
convention among several.

**Model selection is becoming part of the same cost-per-task calculation,**
not a separate choice made on raw benchmark scores: Anthropic's own model
selection guide tells buyers to weigh cost per task against cost per token
per model class, then settle the choice with evals built for the actual
workload rather than a leaderboard number — tying model selection directly
to the per-task attribution and eval-driven decision-making this page
already argues for, from the vendor whose models are being chosen between.

**A benchmarked routing result puts a concrete number on "how much of that
spend is actually justified":** NVIDIA's NeMo Switchyard, tested across 145
agent tasks, found only 7% of turns needed a frontier model — routing the
rest to cheaper models cut total cost 74% for a six-point accuracy
trade-off (see [agent cost](/topic/agent-cost) for the full serving-stack
detail). It sharpens the cost-per-task argument above from "measure spend
per task" to a specific finding: on a typical agent workload, most per-task
spend isn't buying frontier capability the task actually needed.

## What's new
NVIDIA's NeMo Switchyard routing benchmark found only 7% of 145 agent-task
turns actually needed a frontier model, and routing the rest to cheaper
models cut total cost 74% for a six-point accuracy trade-off — a measured
number behind this page's cost-per-task attribution argument (see State of
the art above).

Prior update: Model selection is being folded into the cost-per-task framing directly:
Anthropic's model-choice guidance tells teams to compare model classes on
cost per task (not just cost per token) and settle the trade-off with evals
built for their own workload — connecting the ROI-attribution instinct this
page tracks to the model-selection decision itself, not just to spend
monitoring after the model is already chosen.

## Why it matters for platform engineers
Platform engineers cannot justify AI budgets on vague productivity claims alone. They must build the instrumentation to track cost-per-task, measure execution efficiency against human labor costs, and prevent token runaway. 

When evaluating model downshifting or quantization optimizations, platform engineers must calculate cost based on total tokens consumed in the trace, rather than the sticker price per token, to avoid the hidden trap of token inflation.
