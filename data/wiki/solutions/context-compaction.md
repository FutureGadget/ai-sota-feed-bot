---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: []
updated: 2026-11-28
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
managed at three points: at the input boundary (trimming logs, page trees, and
large JSON tool results before the agent reads them, and saying what was cut),
inside the window (rolling summaries, lazy-loaded skills, subagents), and in
the persistent store (offload the full history to an archive or
[vector/graph KB](/topic/vector-kb) and rehydrate on demand).

**Compaction is moving into the KV cache.** Instead of summarizing history,
serving-layer methods drop or mask cache segments without re-prefilling the
kept context, or store compact hidden states and decode them back into KV.
These skip the lossy rewrite step, but reported gains are mostly from
preprints on single benchmarks.

**Frequent compaction costs less accuracy than feared.** NVIDIA reports 16K
contexts with frequent compaction lose little accuracy, and learning from
past sessions in a repo cut coding-agent cost 18-31%. Stale context is the
bigger hazard: obsolete TODOs and docs pull agents into side-quests.

**The compactor is a safety surface.** Summaries can drop governance
constraints, a false approval in a handoff summary can cause unauthorized
actions, and a history edited to look clean lowers recovery when the world
still holds the error. Pin permissions and hard limits outside the
compactible window and treat summary output as untrusted.

**Skipping compaction is a real option for some runs.** Native 1M-token
windows and recursive dispatch over context chunks avoid the lossy step, but
a longer window still resets between sessions and does not replace durable
memory.

The open problem is fidelity: knowing what a summary lost before a later step
needs it. Measuring compaction loss per task is still mostly manual.

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
