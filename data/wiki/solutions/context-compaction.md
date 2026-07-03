---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac, 8688a4c832b1b52a]
updated: 2026-07-02
covers_evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac, 8688a4c832b1b52a]
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
A structurally different move than compressing the window is **not filling it at
all**: Deep Agents' recursive-language-model (RLM) pattern has the agent write
code that dispatches subagents over chunks of context instead of loading
everything into one window, fixing "context rot" by keeping any single call's
context small rather than summarizing a large one after the fact — a
complement to compaction, not a replacement, since each dispatched chunk still
benefits from being kept lean (see [agent memory](/topic/agent-memory)).

## What's new
A structurally different move complements rather than replaces compaction:
Deep Agents' recursive-language-model (RLM) pattern has the agent dispatch
subagents over context chunks via generated code, so no single call ever
holds the full window — fixing context rot by keeping each call's context
small rather than summarizing a large one after the fact, with each
dispatched chunk still benefiting from being kept lean. That sits alongside
the standing safety finding that compaction can silently erase governance
constraints ("Governance Decay") and input-boundary trimming (Logslim).

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
[prompt injection](/topic/prompt-injection)). The RLM chunk-dispatch
alternative avoids that summarization risk but trades it for orchestration
overhead — each chunk read becomes its own subagent call, so the cost shifts
from lossy-summary risk to sub-call multiplication (see
[agent cost](/topic/agent-cost)).

## Why it matters for platform engineers
Often the highest-leverage first move: it directly attacks token cost and latency
(the bill scales with context size) without standing up new infrastructure. The
risk is silent quality loss, so it needs evaluation — which makes it a tuning
knob, not a set-and-forget fix.
