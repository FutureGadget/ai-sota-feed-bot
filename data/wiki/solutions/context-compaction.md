---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c]
updated: 2026-06-22
covers_evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c]
---

## TL;DR
Keep memory *inside* the context window but small: summarize old turns,
compress history, and deliberately curate what stays in-context each step
("context engineering"). The agent forgets less because the working set is
chosen, not just truncated.

## State of the art
"Context engineering and memory management" has emerged as a discipline of its
own — treating the prompt as a managed working set rather than an append-only
log. Techniques range from rolling summarization to LLM-guided compression of
long-term memory (MemRefine) and memory systems that explicitly model
**association, forgetting, and synthesis** rather than storing everything.
Compaction is increasingly paired with an external store: compress the working
set, offload the rest to a [vector/graph KB](/topic/vector-kb), and rehydrate on
demand. A complementary, cheaper move is compaction at the **input boundary** —
shrinking a tool result *before* it ever enters the context, not summarizing it
afterward. Coding agents read verbose build/test logs, so deterministic
pre-compactors that strip noise from that output (Logslim) cut the per-step token
bill with no model call and no lossy summarization of the agent's own reasoning.

## What's new
Compression is getting smarter than naive summarization — LLM-guided methods
(MemRefine) and forgetting/synthesis-aware memory systems aim to preserve signal
density rather than just shrink token count — and compaction is moving to the
tool-output boundary, deterministically trimming verbose build/test logs before
the agent reads them (Logslim) so the cheapest tokens are the ones never added.

## Trade-offs
Cheap on infra (no external store) and keeps everything the model needs in one
place, but summarization is lossy and irreversible — a detail dropped early can't
be recovered later, and aggressive compaction can quietly degrade task fidelity.
Best for single-session, long-horizon tasks where recency dominates and the full
history isn't needed verbatim.

## Why it matters for platform engineers
Often the highest-leverage first move: it directly attacks token cost and latency
(the bill scales with context size) without standing up new infrastructure. The
risk is silent quality loss, so it needs evaluation — which makes it a tuning
knob, not a set-and-forget fix.
