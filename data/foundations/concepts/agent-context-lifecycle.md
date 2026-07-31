---
slug: agent-context-lifecycle
title: "Why does adding more context sometimes hurt an agent?"
question: "Why does adding more context sometimes hurt an agent?"
summary: "Most production agent failures trace back to unmanaged context, not weak reasoning — treating context as a lifecycle to architect, ingest, scope, anticipate, and compact (not a log to truncate when it gets too big) is what keeps token cost linear instead of quadratic without paying for it in accuracy."
status: active
cluster: memory
updated: 2026-07-31
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
    note: "Argues production agent failures are less often a reasoning problem than a failure to manage what's in the context: conversation histories, large prompts, large tool definitions, and ballooning tool outputs. Decomposes context management into five primitives — architecting, ingesting, scoping, anticipating, and compacting/consolidating. Naive accumulation grows total session token cost quadratically with turn count; plain summarization flattens this to linear cost but introduces an 'accuracy cliff' as specific facts and provenance get dropped; only compaction validated against what must be preserved achieves linear cost without the cliff. The paper's reference implementation (Maximem Synap) scores 92% on LongMemEval and 93.2% on LoCoMo, and the authors note existing memory benchmarks under-measure latency efficiency, token efficiency, and context-rot resistance."
  - id: story-fae52c3b17c1c504-agentic-context-management
    kind: story
    sid: fae52c3b17c1c504
  - id: openai-2026-arc-agi-3-retained-reasoning-compaction
    kind: primary-doc
    title: "How enabling two settings tripled our scores on the ARC-AGI-3 benchmark"
    url: "https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores"
    note: "OpenAI reports GPT-5.6 Sol scored 13.3% on the ARC-AGI-3 public set with the stock harness on the Responses API, then 38.3% once two settings were enabled: retained reasoning (chaining previous_response_id so private reasoning items carry over between turns instead of the model restarting cold on each move) and compaction (summarizing dialogue state instead of hard-truncating the oldest messages once context passes roughly 175K characters). Output tokens per game fell by roughly 6x at the same time score roughly tripled. OpenAI is explicit these are self-reported numbers on their own harness, not an independently verified ARC-AGI-3 leaderboard entry."
  - id: story-265c6a0134aba9b6-arc-agi-3-two-settings
    kind: story
    sid: 265c6a0134aba9b6
  - id: agent-context-lifecycle-editorial-synthesis
    kind: editorial-inference
    title: "Lifecycle framing vs. single-stage fixes"
    note: "Editorial synthesis: a summarizer alone addresses only the compacting stage of the five-stage lifecycle. It still leaves ingestion and scoping unmanaged, which is why teams that bolt on summarization as their only context-cost fix keep hitting the same accuracy cliff the paper describes — the fix has to span all five stages, not just the last one."
covers_evidence: [menlo-context-lifecycle-2026, story-fae52c3b17c1c504-agentic-context-management, openai-2026-arc-agi-3-retained-reasoning-compaction, story-265c6a0134aba9b6-arc-agi-3-two-settings, agent-context-lifecycle-editorial-synthesis]
---

## Builder consequence

When an agent starts failing on long-running or larger tasks, the fix is usually not "make it reason better" — it's rearranging what's in its context. Reaching for a summarizer alone treats one stage of a five-stage lifecycle problem and leaves the other four unmanaged, which is why "just summarize the history" so often trades reliability for a lower token count instead of fixing the root cause.

## Short answer

Production agent failures mostly come from unmanaged context, not weak reasoning. Treat context as something you architect, ingest, scope, anticipate, and compact — not a single log you truncate when it gets too big. Naive accumulation grows token cost quadratically with turns; only a compaction step that's validated against what must survive achieves linear cost without paying for it in accuracy.

## Builder model

Think of an agent's context like a working set, not a transcript. You don't just delete things when it gets full — you decide upfront what data structure holds it (a flat log vs. a structured store), what's allowed to enter and in what form, what's scoped as relevant to the current step versus the whole session, what's proactively prefetched before it's needed, and finally how it gets compacted without losing the provenance of the facts you kept. Those are the five primitives: architecting, ingesting, scoping, anticipating, and compacting/consolidating. Skipping straight to the last one is the common mistake.

## Mechanism

Each new agent turn re-sends (or attends over) the accumulated history, so a session that naively accumulates context grows its total token cost quadratically with turn count — cost per turn keeps rising as the history keeps growing. Periodic summarization collapses that history into something shorter, flattening the curve back to linear, but every summarization pass is lossy: specific numbers, exact facts, and the provenance of where a fact came from can silently disappear. Performance holds while the loss stays below some threshold, then drops sharply once too much detail is gone — an "accuracy cliff" rather than a graceful degradation. The paper's claim is that only compaction validated against what needs to be preserved before it's committed gets you linear cost without the cliff, and that validation only works if the other four stages (deciding structure, admission, and scope ahead of time) already constrain what the compactor is allowed to lose.

OpenAI's own ARC-AGI-3 write-up shows both halves of that claim in a single, concrete production setting. Their stock agent harness discarded the model's private reasoning after every move, so GPT-5.6 Sol effectively restarted cold each turn instead of building on what it had already ruled out or learned about the puzzle — an ingestion failure, in the paper's terms, not a reasoning one. Chaining `previous_response_id` to retain that reasoning across turns, combined with a compaction step that summarizes dialogue state instead of hard-truncating the oldest messages once context passes roughly 175K characters, took the same model's ARC-AGI-3 public-set score from 13.3% to 38.3% while cutting output tokens per game by roughly 6x. Hard truncation and cold-restart-every-turn are exactly the naive, unmanaged patterns the lifecycle framing predicts will underperform.

## Evidence

The reference implementation built around this five-stage lifecycle (Maximem Synap) scores 92% on LongMemEval and 93.2% on LoCoMo, offered as evidence that lifecycle-managed context beats flat-history-plus-summarization baselines on long-memory recall. The authors are explicit that this recall win doesn't by itself certify production readiness: existing memory benchmarks, including the ones just cited, don't measure latency efficiency, token efficiency, or context-rot resistance, so a high recall score can still hide an expensive or slow pipeline.

OpenAI's ARC-AGI-3 result adds a second, independent data point from a different lab and a different task class (long-horizon puzzle-solving rather than conversational recall): retaining reasoning state and validating compaction against a size threshold rather than hard-truncating produced a roughly 3x score gain with 6x fewer output tokens on the same model. Treat the specific percentages carefully — OpenAI reports them on its own harness, not on ARC-AGI-3's independently verified leaderboard, so the number is evidence the mechanism works, not a certified capability claim.

## How to apply

- Decide the data structure that will hold context long-term — a session log vs. a structured fact store — before writing a summarizer; that architecture choice, not the compaction step, determines what's recoverable later.
- Instrument token cost per turn and watch for the quadratic-growth signature (rising marginal cost per turn) as the earliest sign context is being naively accumulated rather than managed.
- Validate any compaction or summarization step against a held-out set of facts it must preserve before shipping it — don't accept a summarizer that "reads fine" without checking recall on the specific facts downstream steps depend on.
- If your API or framework supports carrying reasoning/state across turns (e.g. response-chaining instead of replaying raw history), prefer it over re-deriving state from scratch each turn — discarding reasoning between turns is an ingestion-stage failure, not just a cost inefficiency.
- Trigger compaction on a validated size threshold and summarize, rather than hard-truncating the oldest messages once a context window fills up.
- Measure latency and token cost alongside recall; a benchmark score like LongMemEval/LoCoMo tells you nothing about whether the pipeline is fast or cheap enough to run in production.

## Failure modes

- Treating "add a summarizer" as the whole fix: it addresses only the compacting stage and still lets ungoverned ingestion and scoping cause the accuracy cliff downstream.
- Reading a recall-benchmark win as proof the pipeline is production-ready, when the benchmark doesn't measure latency, token efficiency, or context-rot resistance.
- Assuming quadratic cost growth is a serving-layer problem fixable with caching or batching, when it's actually a context-architecture problem that compounds regardless of how fast the serving stack is.
- Discarding a model's intermediate reasoning between turns by default (replaying only raw messages) and mistaking the resulting cold restarts for a model capability limit rather than a harness design choice.
- Citing a lab's self-reported, own-harness benchmark jump as a verified capability gain instead of what it actually demonstrates: that the mechanism (retained reasoning plus validated compaction) works, independent of the exact percentage.

## Related

- [/topic/agent-memory](/topic/agent-memory) — why agents forget across steps and sessions.
- [/topic/agent-cost](/topic/agent-cost) — why agent token cost is a function of behavior, not request count.
- `context-compaction-safety` — the sibling case where compaction breaks a long-running agent's safety constraints rather than its factual recall.
- `benchmark-production-reliability-gap` — more on why a benchmark score, self-reported or otherwise, needs independent verification before it becomes a production capability claim.
