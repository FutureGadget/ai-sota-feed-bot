---
slug: proving-agent-roi
kind: obstacle
title: "Proving agent ROI and measuring cost efficiency is hard"
area: cost
status: active
solutions: [cost-controls, llm-as-judge]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: per-task-attribution
    title: Metering spend per user, project, and session
    summary: Session-level meters, self-hosted gateways, and platform governance hubs push spend attribution below the account aggregate, the data a cost-per-task case needs.
  - key: roi-metric
    title: Converging on cost per successful task as the ROI metric
    summary: Finance and model vendors now frame ROI and model choice as cost per successful task, settled by workload-specific evals rather than per-token price or leaderboards.
  - key: outcome-evidence
    title: Outcome case studies, and the rollout that raised spend
    summary: Vendor-published case studies report productivity and conversion gains, but a 3,500-engineer rollout that raised spend ~60% shows unattributed deployment can erase them.
---

## TL;DR
Calculating the true return on investment (ROI) for agent systems is blocked by
the difficulty of measuring time savings, tracking per-task token usage, and
accounting for hidden costs like token inflation in quantized models. Platform
engineers must move from generic productivity claims to instrumented
cost-per-task accounting and evidence-based measurement of outcomes.

## State of the art
**The ROI vocabulary is converging on cost per successful task.** OpenAI's
CFO proposes it as a core scorecard metric, and Anthropic tells buyers to pick
models on cost per task, settled by their own evals rather than a
leaderboard. Proving ROI means attributing spend and outcome to the same unit
of work.

**Attribution tooling now reaches that unit.** Open-source meters attribute
tokens to a pull request or a coding agent. Vendor consoles, self-hosted
gateways, and platform governance hubs track spend per user and project and
surface untagged spend, the gap that breaks chargeback.

**The cost side has hidden traps.** Per-token savings can vanish in total
tokens: quantized reasoning models emit more of them. Measured splits show
how much spend buys nothing: only about 7% of agent turns needed a frontier
model, and dropping a central orchestrator cut multi-agent cost about half.

**The outcome side is still mostly vendor case studies.** Reported numbers
include a 21% engineering productivity lift and a 250% conversion lift with
40 hours saved per rep. Each is a single, vendor-published customer figure.

**The counter-example is the most useful data point.** A frontier
coding-model rollout to about 3,500 engineers raised total coding spend
about 60%, because the model helps on complex work but not the medium- and
low-complexity majority. The fix was a budget tier steering the model to
tasks where it pays off: cost-per-task attribution, applied after the fact.

**The open problem is independent, per-task instrumentation on the outcome
side.** Spend is now measurable per task; value delivered per task mostly is
not.

## Why it matters for platform engineers
Platform engineers cannot justify AI budgets on vague productivity claims.
They need instrumentation that tracks cost per task, measures outcomes
against the labor they replace, and stops token runaway.

When evaluating a model downshift, routing policy, or quantization, cost it
on total tokens consumed in the trace, not the sticker price per token. Roll
out expensive models by task tier, with attribution in place first, rather
than blanket deployment. See [cost controls](/topic/cost-controls) and
[agent cost](/topic/agent-cost).
