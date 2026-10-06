---
slug: agent-model-routing
title: "When should an agent route a call to a cheaper model instead of the frontier model?"
question: "When should an agent route a call to a cheaper model instead of the frontier model?"
summary: "Production routers converge on one shape: classify each call or thread cheaply, default to a smaller model, and escalate to frontier only on a specific signal. Reported cost cuts run 30-74%, but the classifier's own cost can eat a fifth of the savings."
status: active
cluster: operations
updated: 2026-10-06
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
    added: 2026-08-19
    note: "145 multi-step agentic tasks (tau-squared-bench airline, BFCL; 6.3 calls each) under escalation-mode routing. A 30B model handled 93% of calls; Claude Opus 4.8 handled 7%. Cost fell 74% versus Opus-only ($0.026 vs $0.092 per task) for a 6-point accuracy drop (86.0% to 80.0%). The frontier model still took 68.4% of spend, and the escalation judge alone was 21.2% of routed spend."
  - id: databricks-2026-unity-ai-gateway-smart-routing
    kind: primary-doc
    title: "Smart Routing in Unity AI Gateway"
    url: "https://www.databricks.com/blog/smart-routing-unity-ai-gateway-match-frontier-quality-30-lower-cost-task"
    added: 2026-08-19
    note: "A small extractor model labels task complexity once at session start; the session defaults to a medium model and escalates only when labels call for frontier capability. Vendor-reported: 35% savings on internal benchmarks, 56% on public benchmarks, Opus 5 quality at under half the cost."
  - id: langchain-2026-open-swe-model-router
    kind: production-field-report
    title: "How to Build a Model Router in the Harness"
    url: "https://www.langchain.com/blog/how-to-build-a-model-router-in-the-harness"
    sid: "378de5b0a4ef1ffb"
    added: 2026-10-02
    note: "Live A/B of a harness-middleware router in Open SWE: one classifier decision per thread into fast, balanced, or performance tiers. Across 973 threads, median cost fell 64% ($0.94 vs $2.61); merged-PR rate held (29.2% vs 27.3%, p = 0.49). A fast-only arm was stopped after a day over quality complaints. Caveats: no mid-thread re-routing, sparse user feedback, criteria tied to Open SWE's task mix."
  - id: story-b6461cff58b0d468-glean-model-routing
    kind: story
    sid: b6461cff58b0d468
    title: "Frontier Model Cost and Open-Weights Popularity is Driving Demand for Model Routing"
    added: 2026-08-19
    note: "Glean CEO interview: frontier prices rose 2-4x release over release. Glean's Waldo pre-filter decomposes a query and picks tools before any frontier call, cutting latency 50% and tokens 25%; Glean reports $0.45 per task versus $1.84 for a baseline. Company-reported, no published method."
  - id: story-c26d5834adc52fbd-gartner-inference-cost-forecast
    kind: story
    sid: c26d5834adc52fbd
    title: "Gartner Predicts AI Inference Costs per Agentic Workflow Will Increase More Than Fivefold Through 2028"
    added: 2026-08-19
    note: "Analyst forecast: per-workflow inference cost for agentic AI rises more than 5x by 2028. A projection, not a measurement; it explains why routing is becoming a standing architecture decision."
  - id: agent-model-routing-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-08-19
    note: "LangChain, Databricks, and Glean built routers independently and converge on one shape: classify cheaply before generation, default to a smaller model, escalate on a specific cheap signal rather than task type or user tier. They differ on the trigger's own cost; LangChain's judge alone took over a fifth of routed spend, so routing can move cost into the classifier instead of removing it."
---

## Builder consequence
If every agent call goes to a frontier model, you are overpaying for capability most calls don't need. In LangChain's Switchyard benchmark only **7% of calls** needed the frontier model. Gartner forecasts per-workflow inference cost to rise more than fivefold by 2028, so routing decides whether your unit economics improve or degrade as usage grows.

## Short answer
Route per call or per thread on a live signal, not per task category. Default to a cheap or mid-tier model and escalate to frontier only when a cheap-to-compute signal says the work needs it. Independent routers at LangChain, Databricks, and Glean use this shape and report **30-74% cost cuts**. The shared catch: the classifier or judge that decides escalation has its own cost, and in one benchmark it took 21.2% of routed spend.

## Builder model
Routing is not "pick a cheaper model for this kind of task." Production systems compute a fresh signal and differ mainly in where they compute it:

- **Escalation** (NeMo Switchyard) — start on the cheap model; escalate to frontier after two consecutive negative judge verdicts.
- **Session classification** (Databricks Unity AI Gateway) — a small extractor labels the task once at session start; labels move it up or down from a medium default.
- **Thread classification** (LangChain Open SWE) — one classifier decision per thread picks a fast, balanced, or performance tier.
- **Decomposition** (Glean Waldo) — a pre-filter breaks the query down and picks tools before any frontier call.

Cost lives on the whole escalation path, not only at the model swap.

## Mechanism
Routing works because difficulty is unevenly distributed inside a task. A coding or support task mixes trivial reads with a few hard planning steps, so most calls clear on a small model and cost concentrates in a small share of calls. Switchyard's 93/7 split shows this; the frontier model still took 68.4% of spend on its 7% of calls.

Where the signal is computed sets the tradeoff:

- **Per-call judging** is most precise but runs the judge every turn. Requiring two consecutive negative verdicts filters noisy single failures, at the price of that recurring judge cost.
- **One-time classification** (per session or per thread) is cheap but blind to drift. Open SWE's router does not re-route when a thread changes topic.
- **Pre-generation decomposition** cuts tokens and latency before any model choice, independent of which model handles each step.

Quality has to be measured on an outcome. Open SWE's live A/B showed a **64% lower median thread cost** with merged-PR rate statistically unchanged; a fast-only arm was pulled after a day of user complaints. Its tiers came from the cost-versus-capability frontier and its criteria from its own traces, so neither transfers unchanged to another agent.

## How to apply
- **Route on a live signal, not a static rule.** Use judge verdicts, complexity labels, or a decomposition step; not task category, user tier, or time of day.
- **Budget the classifier's cost.** Measure judge or classifier spend as a line item; if it approaches the savings, move to one-time classification or a smaller judge.
- **A/B the router on an outcome metric.** Compare merged PRs, resolved tickets, or task success between routed and control traffic; cost alone hides quality loss.
- **Derive tiers and criteria from your own traces.** Copying another team's thresholds skips the step that makes routing work.
- **Decide the accuracy trade explicitly.** Switchyard traded 6 points of accuracy for 74% lower cost; write down whether your workload tolerates that before shipping.
- **Re-classify on drift** if one-time classification is used and threads change scope mid-run.

## Failure modes
- Treating routing as a one-time swap to a cheaper model, with no escalation path back to frontier.
- Ignoring the judge's own cost, which can consume a fifth of routed spend.
- Routing on task category or user tier and missing that cost concentrates in a few hard calls.
- Classifying once per thread and assuming the label holds after the topic changes.
- Reporting cost savings without an outcome comparison, and shipping a router that loses more quality than the use case allows.

## Related
See [agent cost](/topic/agent-cost), [cost controls](/topic/cost-controls) for budgeting that pairs with routing, and [replay versus live evaluation of routers](/foundations/model-switching-replay-gap) for why router accuracy needs live-rollout evidence.
