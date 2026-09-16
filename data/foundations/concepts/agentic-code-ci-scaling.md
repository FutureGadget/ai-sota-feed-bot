---
slug: agentic-code-ci-scaling
title: "Why does AI-generated code overwhelm your CI system, and what actually fixes it?"
question: "Why does AI-generated code overwhelm your CI system, and what actually fixes it?"
summary: "Anthropic's own CI job volume grew 25x in six months once Claude was authoring 80% of code changes and engineers shipped 8x more code per quarter — and the bottleneck wasn't compute, it was a single-writer test-selection service that fell behind under load; three incremental patches each bought less time than the last (70 days, then 29, then under a day) until a stateless, journal-based redesign scaled cleanly."
status: active
cluster: operations
updated: 2026-09-16
audience: "strong-software-engineer"
math_depth: ""
related_topics: [agent-cost, agent-reliability, agent-tracing]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: anthropic-2026-ci-test-impact-analysis
    kind: primary-doc
    title: "Agentic coding is straining CI. Here's how we scaled test impact analysis at Anthropic"
    url: "https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic"
    note: "Anthropic's own engineering account: CI job volume grew 25x over six months as Claude authored 80% of code changes and engineers shipped 8x more code per quarter than in 2021-2025, with test volume growing 10x. Their test-selection service paired a listener (records every CI result) with a selector (picks which tests a PR needs based on historical test-to-code mapping), but a single writer had to apply every result, so it couldn't scale horizontally; a lag as small as 20 minutes left tens of thousands of test updates unapplied, causing undetected failures to merge into main and flaky tests to block unrelated PRs. Three sequential patches each bought less runway than the last: a bigger machine (October) lasted about 70 days, sharding the listener by package (February) lasted 29 days, and forcing daily restarts for memory pressure (March) lasted under a day, with the service falling over an hour behind during each restart and losing unrecorded results. The eventual fix was a redesign, not another patch: an in-memory data store became the source of truth, listener workers went fully stateless (any worker can process any result, appending it to a journal and moving on without holding state), a separate consumer rolls the journal into per-test history every few seconds, and the selector queries the data store directly. One engineer built it in three weeks, versus a quarter for the prior architecture. The post-redesign backlog graph went from growing week over week to flat. Anthropic's own stated lesson: budget for 10-20x perceived scale in a v0 design, not the actual multiplier you expect, because agent-driven throughput growth compounds faster than incremental capacity patches can track."
  - id: story-86abcc6f17fc520e-anthropic-ci-scaling
    kind: story
    sid: "86abcc6f17fc520e"
  - id: agentic-code-ci-scaling-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "The specific numbers are Anthropic's own CI pipeline. The general lesson generalizes to any stateful aggregation service sitting in an agent-driven pipeline's critical path — a vector index writer, a feedback-label store, an eval-result aggregator — because the structural cause is the same: a single-writer or otherwise unshardable component whose input rate scales with how much code or output agents produce, not with headcount."
covers_evidence:
  - anthropic-2026-ci-test-impact-analysis
  - story-86abcc6f17fc520e-anthropic-ci-scaling
  - agentic-code-ci-scaling-editorial-synthesis
---

## Builder consequence
If agents are writing a growing share of your code (or generating a growing share of any pipeline's output — traces, evals, feedback events), don't assume your existing infrastructure scales linearly with that growth. Anthropic's CI job volume grew 25x in six months once Claude was authoring 80% of code changes; the constraint that nearly broke their pipeline wasn't compute, it was a single-writer service that couldn't be sharded, and incremental fixes to it bought progressively less time each round.

## Short answer
Agent-driven throughput growth is exponential in practice, not linear, because it compounds two multipliers at once: engineers ship more changes, and each change is larger or more automated than before. A service architected for human-paced load — especially one with a single writer or another unshardable bottleneck — degrades from "slow" to "actively wrong" (stale data silently causing undetected failures) well before anyone notices it's out of headroom. Patching capacity (bigger machine, more shards, forced restarts) each buys less runway than the last, because the load curve is still exponential. The fix that actually held was a structural one: make the ingestion path stateless and append-only, and move state and aggregation to a separate, horizontally scalable layer.

## Builder model
- **The bottleneck is rarely the whole pipeline — it's one unshardable component.** Anthropic's test-selection service had two parts: a listener recording CI results and a selector choosing which tests to run. Only the listener's single-writer design was the actual constraint; nothing else in the pipeline needed to change.
- **Small lag becomes large data loss under high throughput.** At their volume, a 20-minute lag meant tens of thousands of test-result updates went unapplied — not "slightly stale," but functionally missing, which let real failures merge undetected and made unrelated tests flaky.
- **Incremental capacity patches have diminishing returns against exponential load.** A bigger machine bought ~70 days, sharding by package bought 29, forced restarts bought under a day — each patch addressed the previous bottleneck without addressing the structural one (a single writer applying every result), so the next bottleneck arrived faster each time.
- **The fix was decoupling ingestion from aggregation, not adding more of the same.** Stateless listener workers append results to a journal; a separate consumer periodically rolls the journal into per-test history. No component holds state that blocks horizontal scaling, at the cost of running a more expensive architecture than the original single-writer service.

## Mechanism
A test-selection (or test-impact-analysis) service needs two things: a record of which tests exercised which code in the past, and a fast way to pick the minimal test set a given change actually needs. The failure mode here isn't in the selection logic — it's in how the historical record gets written. A single writer applying every incoming result is simple and correct at low volume, but its throughput ceiling is fixed by one process's write rate, not by how much hardware you add elsewhere. As input volume grows, the writer falls behind; the gap between "result happened" and "result recorded" grows, and every consumer reading that record (the selector, in this case) is silently working from data that's increasingly wrong rather than just slow.

The redesign's core move is a general pattern for exactly this shape of problem: separate the append-only, horizontally-shardable act of recording an event (any worker can accept and journal any result) from the stateful, harder-to-shard act of aggregating those events into a queryable history (a dedicated consumer rolls the journal forward on its own schedule). Ingestion no longer has a throughput ceiling tied to a single process; aggregation lag becomes a tunable staleness bound instead of an unbounded backlog.

## Evidence
The account is Anthropic's own engineering postmortem of its internal CI pipeline, published on the Claude blog, with specific before/after numbers (25x job growth, three patches and their exact runways, a three-week rebuild time, and a backlog graph going from growing to flat). It is a first-party production account of one company's infrastructure, not an independently replicated study, but it is a primary source describing measured production behavior rather than a benchmark or theoretical claim. The editorial generalization — that this pattern applies to other stateful aggregation services in agent-driven pipelines — is LLM Digest's own inference, not a claim Anthropic makes about other systems.

## How to apply
- **Identify any single-writer or otherwise unshardable component sitting in a pipeline whose input volume scales with agent output.** A results listener, a vector-index writer, an eval-result aggregator, a feedback-label store — anything where "apply this update" has to happen in one place is a candidate.
- **Budget capacity for 10-20x your current estimate of agent-driven growth in a v0 design**, per Anthropic's own stated lesson — not the multiplier you'd plan for human-paced growth, because engineers shipping more agent-authored code compounds with agents themselves generating more of the downstream volume (tests, traces, evals).
- **Treat "falling behind" as a correctness bug, not a performance annoyance**, once a consumer of stale data can make a wrong decision (like skipping a test that should have run). Alert on lag against a hard staleness bound, not just on service uptime.
- **When you're on your second or third capacity patch for the same bottleneck, stop patching and redesign.** Diminishing runway between patches (70 days, then 29, then under a day, in Anthropic's case) is the signal that the architecture, not the capacity, is the constraint.
- **Prefer decoupling append-only ingestion from stateful aggregation** as the default shape for any service that has to keep up with agent-driven event volume — it costs more to run than a single-writer design, but its scaling ceiling is a knob (add consumers, tune journal-rollup frequency), not a rebuild.

## Failure modes
- Scaling a bottlenecked service by adding capacity (bigger machine, more shards of the same design) instead of identifying the actual structural constraint, and getting progressively less runway from each round of scaling.
- Treating a stale data-aggregation lag as a performance metric to shrug off, when downstream consumers making decisions on stale data (a test selector, an eval aggregator) can silently produce wrong outcomes — failures merging undetected, or good changes wrongly blocked.
- Planning infrastructure capacity for the growth rate of your headcount or feature velocity, instead of the growth rate of agent-authored output, which compounds faster and doesn't level off at the same pace.
- Assuming a service that held up fine before agents were writing a large share of your code will keep holding up as that share grows — the load curve shape changes, not just its slope.

## Related
See [agent cost](/topic/agent-cost) and [agent reliability](/topic/agent-reliability) for the broader operational tradeoffs of running agent-driven pipelines at scale, and [agent tracing](/topic/agent-tracing) for the observability layer that would surface a growing aggregation lag before it causes undetected failures.
