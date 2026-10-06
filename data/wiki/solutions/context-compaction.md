---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: curating-the-working-set
    title: Curating what stays in context
    summary: Compaction is becoming one step in a curation discipline that trims tool output at the input boundary, consolidates stored memory, and loads instructions only when needed.
  - key: compaction-safety
    title: The compactor as a safety surface
    summary: Summaries can silently drop safety constraints or carry instructions the model wrote itself, so compaction output needs the same distrust as any untrusted input.
  - key: skipping-compaction
    title: Skipping compaction with bigger windows or recursive dispatch
    summary: 1M-token windows and sub-agent fan-out over context chunks let some long runs avoid compaction, but neither carries memory across sessions.
  - key: compressed-serving
    title: Buying back accuracy lost to compression
    summary: Serving-layer tricks such as asymmetric speculative decoding recover most full-context accuracy while still decoding from a compressed context.
---

## TL;DR
Keep memory *inside* the context window but small: summarize old turns,
compress history, and deliberately curate what stays in-context each step
("context engineering"). The agent forgets less because the working set is
chosen, not just truncated.

## State of the art
Compaction is now treated as **curation, not truncation**. The working set is
managed at three points: at the input boundary (deterministic trimming of
build and test logs before the agent reads them), inside the window (rolling
summaries, lazy-loaded skill instructions), and in the persistent store
(budgeted compression and consolidation that forgets redundant entries).
Practitioners increasingly pair it with an external store: compress the
working set, offload the rest to a [vector/graph KB](/topic/vector-kb), and
rehydrate on demand.

**The compactor is a safety surface.** Summaries can drop governance
constraints the agent obeyed while they were visible, and a model can write
instruction-like text into its own summary. The working practice is to pin
permissions and hard limits outside the compactible window and treat summary
output as untrusted.

**Skipping compaction is now a real option for some runs.** Native 1M-token
windows and recursive dispatch (sub-agents over context chunks) avoid the
lossy step, and one practitioner run held accuracy across 80M tokens with no
compaction. The counterweight: a longer window still resets between sessions,
so it does not replace durable memory.

The open problem is fidelity: knowing what a summary lost before a later step
needs it. Serving-layer work such as asymmetric speculative decoding recovers
most full-context accuracy, but measuring compaction loss per task is still
mostly manual.

## Trade-offs
Cheap on infra (no external store) and keeps everything the model needs in
one place. But summarization is lossy and irreversible: a detail dropped early
can't be recovered later, and aggressive compaction can quietly degrade task
fidelity.

The sharpest failure is lost *constraints*, not lost detail. Anything
load-bearing (permissions, safety limits, the user's hard "do not") must live
outside the compactible window (see [prompt injection](/topic/prompt-injection)).

Best for single-session, long-horizon tasks where recency dominates. Where
the window is large enough, skipping compaction avoids the loss entirely, at
a higher per-call token bill.

## Why it matters for platform engineers
Often the highest-leverage first move: it directly attacks token cost and
latency (the bill scales with context size) without standing up new
infrastructure. The risk is silent quality loss, so it needs evaluation,
which makes it a tuning knob, not a set-and-forget fix. The compactor also
belongs in your threat model: its output feeds every later turn.
