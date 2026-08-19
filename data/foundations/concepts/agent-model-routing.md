---
slug: agent-model-routing
title: "When should an agent route a call to a cheaper model instead of the frontier model?"
question: "When should an agent route a call to a cheaper model instead of the frontier model?"
summary: "Independent routing systems at LangChain, Databricks, and Glean converge on the same shape — classify each call's complexity cheaply, default to a mid-tier model, escalate to frontier only on a specific signal — and each reports 30-75% cost cuts, but the escalation classifier itself can eat a fifth or more of the savings if you don't budget for it."
status: active
cluster: operations
updated: 2026-08-19
audience: "strong-software-engineer"
math_depth: ""
related_topics: [agent-cost, cost-controls]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: langchain-2026-switchyard-agent-routing-benchmark
    kind: benchmark-result
    title: "Agent routing benchmark: NVIDIA NeMo Switchyard"
    url: "https://www.langchain.com/blog/switchyard-agent-routing-benchmark"
    note: "LangChain benchmarked NeMo Switchyard's escalation-mode routing across 145 multi-step agentic tasks (avg. 6.3 model calls each, drawn from tau-squared-bench airline and the Berkeley Function Calling Leaderboard). Only 7% of calls needed the frontier model (Claude Opus 4.8); a 30B model (Nemotron 3.5 Lightning) handled the other 93%. Routing cut cost 74% versus Opus-only ($0.026/task vs $0.092/task) for a 6-point accuracy drop (86.0% to 80.0%). The frontier model still consumed 68.4% of spend despite handling 7% of calls, and the judge model used to decide escalation was itself 21.2% of routed spend."
  - id: databricks-2026-unity-ai-gateway-smart-routing
    kind: primary-doc
    title: "Smart Routing in Unity AI Gateway"
    url: "https://www.databricks.com/blog/smart-routing-unity-ai-gateway-match-frontier-quality-30-lower-cost-task"
    note: "Unity AI Gateway's Smart Routing classifies task complexity once at session start with a small, fast extractor model, not a frontier model, then defaults to a medium-sized model and escalates only when the derived task/language labels call for frontier-level capability. Databricks reports 35% cost savings on internal benchmarking, 56% on public benchmarks, and matching Opus 5 quality at under half the cost."
  - id: story-b6461cff58b0d468-glean-model-routing
    kind: story
    sid: b6461cff58b0d468
    title: "Frontier Model Cost and Open-Weights Popularity is Driving Demand for Model Routing"
    note: "Glean CEO Arvind Jain: frontier model prices have doubled to quadrupled release over release, pushing enterprise per-user AI spend up 10-20x year over year. Glean's own pre-filter model, Waldo, decomposes a query and decides which tools it needs before any frontier call, cutting latency 50% and tokens 25%; Glean reports averaging $0.45/task versus $1.84/task for a comparison baseline."
  - id: story-c26d5834adc52fbd-gartner-inference-cost-forecast
    kind: story
    sid: c26d5834adc52fbd
    title: "Gartner Predicts AI Inference Costs per Agentic Workflow Will Increase More Than Fivefold Through 2028"
    note: "Gartner's market forecast: per-workflow inference cost for agentic AI is projected to rise more than 5x by 2028 — the demand-side pressure that makes routing off the frontier model a default architecture decision rather than a one-time optimization."
  - id: agent-model-routing-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "Read together, LangChain's, Databricks', and Glean's independently built routers converge on one shape: classify complexity cheaply before generation, default to a mid-tier or small model, and escalate to frontier only on a specific, cheap-to-compute signal (a judge model's negative verdict, a complexity label, a decomposition pre-filter) rather than by task type or user tier. The three sources disagree on the escalation trigger's own cost and reliability, not on the routing shape — LangChain's judge model alone consumed over a fifth of routed spend, which is the real caution: naive routing can quietly move the cost problem into the classifier instead of removing it."
covers_evidence:
  - langchain-2026-switchyard-agent-routing-benchmark
  - databricks-2026-unity-ai-gateway-smart-routing
  - story-b6461cff58b0d468-glean-model-routing
  - story-c26d5834adc52fbd-gartner-inference-cost-forecast
  - agent-model-routing-editorial-synthesis
---

## Builder consequence
If every call your agent makes goes to a frontier model, you are almost certainly overpaying for capability most of those calls don't need. LangChain's own benchmark of a production routing system found only 7% of agent turns actually required the frontier model; the other 93% were handled by a 30B model with a 6-point accuracy cost. Gartner is forecasting per-workflow inference cost to rise more than fivefold by 2028, so this stops being a nice-to-have optimization and becomes the difference between an agent that scales and one whose unit economics get worse as usage grows.

## Short answer
Route per call, not per task type: default every call to a cheap or mid-tier model, and escalate to the frontier model only when a specific, cheap-to-compute signal says the current call needs it. Three independently built production routers — LangChain's benchmark of NeMo Switchyard, Databricks' Unity AI Gateway, and Glean's Waldo — all use this shape and report cost cuts between 30% and 74%. The catch in all three: the classifier or judge model that decides when to escalate has its own cost, and in the LangChain benchmark it consumed over a fifth of the routed spend.

## Builder model
Stop thinking of model routing as "pick a cheaper model for this kind of task." None of the three production systems here route by task category. They route by call, using a signal computed fresh each time:

- **LangChain / NeMo Switchyard** — escalation mode: every task starts on the cheap model; after two consecutive negative verdicts from a judge model, it escalates permanently to frontier.
- **Databricks / Unity AI Gateway** — classification mode: a small, fast extractor model labels the task once at session start (affected components, code evidence present, failure pattern, fix scope), and those labels move the session up or down from a medium-sized default.
- **Glean / Waldo** — decomposition mode: a pre-filter model breaks the query down and decides which tools and steps are needed before any frontier call happens, trimming tokens and latency even before routing a specific step.

The shared mental model: cost sits on the whole escalation path, not just at the model swap. A router that reduces frontier calls but runs an expensive judge on every turn can spend a large fraction of its "savings" running the judge itself.

## Mechanism
LangChain's escalation mode starts every task on Nemotron 3.5 Lightning (30B parameters) and only escalates to Claude Opus 4.8 after two consecutive negative verdicts from a separate judge model — a design meant to keep single unreliable outputs from triggering an expensive escalation, at the cost of running that judge on every turn. Across 145 multi-step agentic tasks (tau-squared-bench airline, Berkeley Function Calling Leaderboard), 93% of the 6.3 average calls per task never left the cheap model.

Databricks' Smart Routing runs classification once, at session start, rather than per call: a lightweight extractor model reads the task description and produces semantic labels (system components, code evidence type, failure pattern, fix localization, project type), which the router turns into task and language "families." The session defaults to a medium-sized model and moves up only when those labels indicate frontier-level capability is required — trading some per-call precision for a cheaper, one-time classification cost.

Glean's Waldo model sits earlier in the pipeline: before any frontier call, it decomposes the incoming query and decides which tools and steps the task actually needs, which is what produces the reported 50% latency cut and 25% token cut independent of which model eventually handles each step.

## Evidence
- Benchmark-result-backed (LangChain): a controlled 145-task benchmark of NeMo Switchyard's escalation routing, with exact cost, accuracy, and spend-distribution numbers.
- Primary-doc-backed (Databricks): the vendor's own account of Unity AI Gateway's session-start classification mechanism and reported cost savings.
- Story-backed (Glean, via Latent Space interview): CEO Arvind Jain's account of Waldo's decomposition-based pre-filtering and Glean's per-task cost comparison.
- Story-backed (Gartner, via press release): a market forecast establishing why routing's cost pressure is expected to grow, not just a snapshot of current savings.
- Editorial inference: that these three independently built systems share one underlying shape, and that the escalation/classification step's own cost is the shared risk, is LLM Digest's synthesis across three differently designed routers.

## How to apply
- **Route per call, not per task type.** A single "coding agent" task mixes trivial file reads with genuinely hard planning steps; routing by task category misses that most of the cost concentrates in a small share of calls within any task.
- **Budget the classifier or judge's own inference cost.** LangChain's judge model consumed 21.2% of routed spend — a naive routing implementation can silently reintroduce much of the savings you're chasing if the escalation signal itself isn't cheap.
- **Pick an escalation signal you can compute cheaply and repeatedly**: consecutive judge failures (LangChain), task-complexity labels derived once at session start (Databricks), or a decomposition pre-filter before any frontier call (Glean) — not a static allowlist of task types.
- **Decide the accuracy tradeoff explicitly before shipping.** LangChain's benchmark traded 6 points of accuracy (86.0% to 80.0%) for a 74% cost cut; that trade is acceptable for some workloads and not others, and it should be a deliberate choice, not a side effect.
- **Treat routing as infrastructure that has to keep working as usage grows**, not a one-time tuning pass — Gartner's forecast of a fivefold rise in per-workflow inference cost by 2028 is the reason all three vendors here shipped routing as a standing product feature rather than a manual cost-cutting exercise.

## Failure modes
- Treating model routing as a one-time model swap (send everything to a cheaper model) instead of a per-call decision with a real escalation path back to frontier capability.
- Ignoring the classifier or judge model's own inference cost, which can consume a fifth or more of total routed spend and quietly erode the savings the router was built to capture.
- Routing on a static rule (task category, user tier, time of day) instead of a live complexity or confidence signal, missing that cost concentrates in a small share of genuinely hard calls regardless of task type.
- Optimizing for cost without measuring the accuracy delta, and shipping a router that trades away more quality than the use case can tolerate.

## Related
See [agent cost](/topic/agent-cost) for the broader problem of runaway agent token spend this concept is one mitigation for, and [cost controls](/topic/cost-controls) for budgeting and per-task attribution techniques that pair with routing rather than replace it.
