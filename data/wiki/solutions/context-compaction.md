---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac]
updated: 2026-06-24
covers_evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac]
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
The newest finding is that compaction is not just lossy but **safety-critical**:
"Governance Decay" shows that summarizing, evicting, or compressing context in a
long-horizon agent can silently drop the very safety/governance constraints that
were stated up front, so a later step acts as if rules it was given hours ago no
longer apply — the compactor is a security surface, not just a cost optimization.

## What's new
Compaction now has a documented **safety** failure mode: "Governance Decay" shows
that context summarization/eviction in long-running agents can silently erase the
safety and governance constraints set earlier in the session, reframing the
compactor as a security-critical layer that needs constraint-preserving
guarantees — not just a token-saving one. That sits alongside smarter compression
(LLM-guided MemRefine, forgetting/synthesis-aware stores) and input-boundary
trimming of verbose tool output (Logslim).

## Trade-offs
Cheap on infra (no external store) and keeps everything the model needs in one
place, but summarization is lossy and irreversible — a detail dropped early can't
be recovered later, and aggressive compaction can quietly degrade task fidelity.
Best for single-session, long-horizon tasks where recency dominates and the full
history isn't needed verbatim. The sharpest failure mode is **not** lost task
detail but lost *constraints*: Governance Decay shows compaction can quietly evict
the safety/policy rules an agent was given up front, so over a long session it
drifts out of its guardrails — which means anything load-bearing (permissions,
safety limits, the user's hard "do not") must be pinned outside the compactible
window, not left to survive summarization (see
[prompt injection](/topic/prompt-injection)).

## Why it matters for platform engineers
Often the highest-leverage first move: it directly attacks token cost and latency
(the bill scales with context size) without standing up new infrastructure. The
risk is silent quality loss, so it needs evaluation — which makes it a tuning
knob, not a set-and-forget fix.
