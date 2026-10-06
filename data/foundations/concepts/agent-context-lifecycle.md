---
slug: agent-context-lifecycle
title: "Why does adding more context sometimes hurt an agent?"
question: "Why does adding more context sometimes hurt an agent?"
summary: "Most production agent failures trace back to unmanaged context, not weak reasoning. Treating context as a lifecycle to architect, ingest, scope, anticipate, and compact keeps token cost linear instead of quadratic without paying for it in accuracy."
status: active
cluster: memory
updated: 2026-10-06
audience: "strong-software-engineer"
math_depth: ""
related_topics: [agent-memory, agent-cost]
related_playbook_cards: [pb-context-lifecycle-not-storage]
related_storylines: []
evidence:
  - id: menlo-context-lifecycle-2026
    kind: benchmark-result
    title: "Agentic Context Management: Solving Agent Memory and Cost by Treating Them as Lifecycle and Architecture Problems"
    url: "http://arxiv.org/abs/2607.21503"
    sid: "fae52c3b17c1c504"
    added: 2026-07-24
    note: "Splits context management into five primitives: architecting, ingesting, scoping, anticipating, compacting. Naive accumulation grows session token cost quadratically with turns; plain summarization flattens it to linear but hits an accuracy cliff as facts and provenance drop. Only compaction validated against what must survive avoids both. The reference implementation (Maximem Synap) reports 92% on LongMemEval and 93.2% on LoCoMo; the authors note those benchmarks ignore latency, token efficiency, and context-rot resistance."
  - id: openai-2026-arc-agi-3-retained-reasoning-compaction
    kind: primary-doc
    title: "How enabling two settings tripled our scores on the ARC-AGI-3 benchmark"
    url: "https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores"
    sid: "265c6a0134aba9b6"
    added: 2026-07-31
    note: "GPT-5.6 Sol went from 13.3% to 38.3% on the ARC-AGI-3 public set after two harness settings: retained reasoning (chaining previous_response_id so reasoning carries across turns) and compaction (summarizing dialogue state instead of hard-truncating past roughly 175K characters). Output tokens per game fell about 6x. Vendor-reported on OpenAI's own harness, not an independently verified leaderboard entry."
  - id: gaggar-2026-protocol-preserving-context-trimming
    kind: benchmark-result
    title: "Protocol-Preserving Context Trimming for Agentic Workflows: Benefits, Failure Regimes, and Budget Guardrails"
    url: "http://arxiv.org/abs/2609.16461v1"
    sid: "a3b54d5a91acaa5a"
    added: 2026-09-23
    note: "Compares five trimming strategies. Recency, relevance, and summarization saved about 60% of tokens but reached only 66.6-77.3% task success. Protocol-aware trimming reached 92.2%; adaptive budget guardrails reached 96.0% success and 1.0% cascading failure at 56.0% savings. Retained budgets at or below 25% raised failure odds 10.92-fold versus 50% or more (p < 0.001); safe thresholds rose with workflow complexity. Single-author study on its own workflow suite, so treat odds ratios as directional."
  - id: agent-context-lifecycle-editorial-synthesis
    kind: editorial-inference
    title: "Lifecycle framing vs. single-stage fixes"
    added: 2026-07-24
    note: "Editorial synthesis: a summarizer alone addresses only the compacting stage of the five-stage lifecycle. Ingestion and scoping stay unmanaged, which is why teams that bolt on summarization as their only context-cost fix keep hitting the same accuracy cliff."
---

## Builder consequence

When an agent fails on long-running or larger tasks, the fix is usually rearranging what is in its context, not making it reason better. A summarizer alone treats one stage of a five-stage lifecycle and often trades reliability for a lower token count without fixing the root cause.

## Short answer

Production agent failures mostly come from unmanaged context, not weak reasoning. Treat context as something you architect, ingest, scope, anticipate, and compact, not a log you truncate when it fills up.

- Naive accumulation grows token cost quadratically with turns.
- Plain summarization makes cost linear but loses facts past a threshold.
- Compaction validated against what must survive gets linear cost without the accuracy loss.

How much context you keep is a reliability parameter: one trimming study found budgets at or below 25% raised failure odds nearly 11-fold versus 50% or more.

## Builder model

Treat context as a working set, not a transcript. Five decisions shape it:

1. **Architect** — what structure holds it (flat log vs. structured fact store).
2. **Ingest** — what may enter, and in what form.
3. **Scope** — what is relevant to this step versus the whole session.
4. **Anticipate** — what to prefetch before it is needed.
5. **Compact** — how to shrink it without losing the provenance of kept facts.

Skipping straight to step 5 is the common mistake.

## Mechanism

**Cost grows quadratically.** Each turn re-sends or attends over the accumulated history, so per-turn cost keeps rising and total session cost grows with the square of turn count.

**Summarization is lossy with a cliff.** Collapsing history flattens cost to linear, but each pass can drop specific numbers, exact facts, and where a fact came from. Performance holds until too much is gone, then falls sharply. The fix is compaction checked against what must be preserved, and that check only works if architecture, ingestion, and scope already constrain what the compactor may lose.

**Harness choices look like capability limits.** OpenAI's ARC-AGI-3 write-up shows a stock harness discarding the model's private reasoning after every move, so the model restarted cold each turn. Retaining reasoning across turns and summarizing instead of hard-truncating took GPT-5.6 Sol from 13.3% to 38.3% with about 6x fewer output tokens (vendor-reported). Cold restarts and hard truncation are exactly the unmanaged patterns the lifecycle view predicts will underperform.

**Cutting the right tokens beats cutting the most.** In the protocol-preserving trimming study, recency, relevance, and summarization strategies saved about 60% of tokens but reached only 66.6-77.3% task success. Trimming that preserves state the interaction protocol depends on reached 92.2%; adding an adaptive budget floor reached 96.0% while still saving 56%. The budget below which failures spike rises with workflow complexity, so a floor tuned on simple workflows under-provisions complex ones.

## How to apply

- **Choose the context structure first.** Decide between a session log and a structured fact store before writing a summarizer; that choice determines what is recoverable later.
- **Watch per-turn token cost.** Rising marginal cost per turn is the earliest sign of naive accumulation.
- **Test compaction against required facts.** Check recall on the specific facts downstream steps depend on, not whether the summary reads well.
- **Carry reasoning across turns.** Prefer response chaining or retained state over replaying raw history.
- **Summarize on a threshold; do not hard-truncate** the oldest messages when the window fills.
- **Keep retained budgets at 50% or more.** If you must go lower, use protocol-aware trimming, not recency or relevance alone.
- **Set the floor per workflow-complexity class**, not one threshold for every agent.
- **Measure latency and token cost next to recall**; LongMemEval and LoCoMo scores say nothing about production cost.

## Failure modes

- Treating "add a summarizer" as the whole fix while ingestion and scoping stay ungoverned.
- Reading a recall-benchmark win as proof of production readiness.
- Treating quadratic cost growth as a serving problem that caching or batching can fix.
- Discarding reasoning between turns and blaming the resulting cold restarts on the model.
- Citing a self-reported, own-harness score jump as a verified capability gain.
- Optimizing trimming for token savings alone: the highest-savings strategies had the lowest task success.
- Using one fixed retained-context floor for workflows of different complexity.

## Related

- [/topic/agent-memory](/topic/agent-memory) — why agents forget across steps and sessions.
- [/topic/agent-cost](/topic/agent-cost) — why token cost tracks agent behavior.
- `context-compaction-safety` — compaction breaking safety constraints instead of recall.
