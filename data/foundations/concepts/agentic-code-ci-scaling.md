---
slug: agentic-code-ci-scaling
title: "Why does AI-generated code overwhelm your CI system, and what actually fixes it?"
question: "Why does AI-generated code overwhelm your CI system, and what actually fixes it?"
summary: "Anthropic's CI job volume grew 25x in six months as Claude wrote 80% of code changes. The bottleneck was a single-writer test-selection service; three capacity patches bought 70, 29, then under one day until a stateless, journal-based redesign held."
status: active
cluster: operations
updated: 2026-10-06
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
    sid: "86abcc6f17fc520e"
    added: 2026-09-16
    note: "Anthropic's account of its own CI: job volume up 25x in six months, Claude writing 80% of changes, 8x more code per quarter. A single-writer test-selection listener fell behind; 20 minutes of lag left tens of thousands of results unapplied, letting failures merge. Patches lasted about 70 days, 29 days, then under a day. A stateless, journal-based redesign, built by one engineer in three weeks, flattened the backlog. First-party, single-company report."
  - id: agentic-code-ci-scaling-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-09-16
    note: "The numbers are Anthropic's own pipeline. The lesson extends to any stateful aggregation service in an agent-driven critical path, such as a vector-index writer, feedback-label store, or eval-result aggregator: a single-writer or unshardable component whose input rate scales with agent output, not headcount."
---

## Builder consequence
If agents write a growing share of your code or pipeline output, your infrastructure will not scale linearly with that growth. Anthropic's **CI job volume grew 25x in six months** once Claude wrote 80% of code changes. What nearly broke the pipeline was not compute but one single-writer service, and each capacity patch bought less time than the last.

## Short answer
Agent-driven load compounds: engineers ship more changes, and each change generates more downstream work. A service built for human-paced load, especially one with a single writer, degrades from slow to silently wrong before anyone sees it is out of headroom. Capacity patches buy shrinking runway against that curve. The fix that held was structural: stateless, append-only ingestion, with aggregation moved to a separate layer that scales horizontally.

## Builder model
- **One unshardable component is the bottleneck.** In Anthropic's test-selection service, only the single-writer listener needed to change; the selector and the rest of CI were fine.
- **Lag turns into data loss at high throughput.** Twenty minutes behind meant tens of thousands of missing results, so real failures merged and unrelated tests looked flaky.
- **Shrinking runway is the signal.** Bigger machine, then sharding, then forced restarts: about 70 days, 29 days, under a day. Each patch moved the bottleneck without removing it.
- **Decouple ingestion from aggregation.** Stateless workers journal results; a separate consumer rolls the journal into history. It costs more to run than one writer, but scaling becomes a knob instead of a rebuild.

## Mechanism
Test-impact analysis needs a history of which tests exercised which code and a fast way to select the minimal test set for a change. The failure was in writing that history, not in selection. A single writer applying every result is simple and correct at low volume, but its ceiling is one process's write rate, regardless of hardware elsewhere. As input grows, the gap between "result happened" and "result recorded" widens, and every reader of the record works from data that is increasingly wrong, not merely slow.

The redesign is a general pattern. Recording an event becomes append-only and shardable: any worker accepts and journals any result, holding no state. Aggregating events into queryable history becomes a separate consumer that rolls the journal forward every few seconds. Ingestion loses its single-process ceiling, and aggregation lag becomes a tunable staleness bound instead of an unbounded backlog.

## How to apply
- **Find single-writer components whose input scales with agent output**: results listeners, vector-index writers, eval aggregators, feedback-label stores.
- **Design v0 for 10-20x the scale you expect**, Anthropic's stated lesson, because agent-authored output compounds faster than headcount.
- **Treat lag as a correctness bug.** Alert against a hard staleness bound once a stale read can cause a wrong decision, such as skipping a test that should run.
- **Stop patching at the second or third capacity fix for the same bottleneck.** Shrinking runway means the architecture is the constraint.
- **Default to append-only ingestion plus separate aggregation** for services that must keep up with agent-driven event volume.

## Failure modes
- Adding capacity to the same design and getting less runway each round.
- Treating aggregation lag as a performance metric while downstream consumers make wrong decisions on stale data.
- Planning capacity on headcount or feature velocity instead of agent-authored output.
- Assuming a service that worked before agents wrote much code will keep working as that share grows.

## Related
See [agent cost](/topic/agent-cost) and [agent reliability](/topic/agent-reliability) for operating agent-driven pipelines at scale, and [agent tracing](/topic/agent-tracing) for observability that surfaces growing lag before it causes undetected failures.
