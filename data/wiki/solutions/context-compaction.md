---
slug: context-compaction
kind: solution
title: "Context compaction: summarize, compress, and curate the working set"
status: active
obstacles: [agent-memory]
related_storylines: []
evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac, 34c069f2bffc49df, aad81dd5a952ad5d]
updated: 2026-09-04
covers_evidence: [10129892c7fcda0f, 2c8ff757b828dee7, 83e63e463a1dff9d, c763e01254fa7c5c, 9c19b2212d6264ac, 34c069f2bffc49df, aad81dd5a952ad5d]
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
Compaction is not just lossy but **safety-critical**:
"Governance Decay" shows that summarizing, evicting, or compressing context in a
long-horizon agent can silently drop the very safety/governance constraints that
were stated up front, so a later step acts as if rules it was given hours ago no
longer apply — the compactor is a security surface, not just a cost optimization.

A practitioner talk sharpens what to compact rather than only how: "The Right
300 Tokens Beat 100k Noisy Ones" argues coding agents fail from bloated,
stuffed context more often than from a missing capability, and names four
concrete build-discipline fixes alongside summarization itself — lazy-loaded
skills (load a skill's instructions only when the task needs them, not every
turn), versioned context artifacts, an externalized memory bank, and
LLM-as-judge evals to catch quality loss the compaction step introduces. It
treats compaction as one lever inside a broader curation discipline rather
than the whole answer, aimed at engineers turning raw markdown files into
reliable agentic workflows.

**Compaction also has a latency and accuracy cost that a plain
summarize-and-replace approach doesn't have to pay**: AsymSpec targets the
standard assumption that a speculative-decoding draft model and its verifier
must see identical context. By letting a lightweight drafter read the
agent's full, uncompressed input while the large verifier decodes from a
compressed context view — with a divergence-aware acceptance gate to keep
verification stable — it recovers roughly 90% of full-context accuracy at
1.3-1.7x the throughput and 0.2-0.3x the compute cost of decoding on the
full context. It's a direct answer to the standing tension on this page:
compressing an agent's growing context to control cost and latency normally
costs accuracy, and AsymSpec buys most of that accuracy back without
abandoning compression (see [agent latency](/topic/agent-latency) for the
serving-layer mechanics).

## What's new
AsymSpec answers this page's standing compression-vs-accuracy tension with a
context-asymmetric speculative-decoding design: a lightweight drafter reads
the agent's full uncompressed input while the large verifier decodes from a
compressed view, recovering ~90% of full-context accuracy at 1.3-1.7x the
throughput and 0.2-0.3x the compute cost of full-context decoding (see State
of the art above).

Prior update: "The Right 300 Tokens Beat 100k Noisy Ones" reframes compaction as one
lever inside a broader context-curation discipline, alongside lazy-loaded
skills, versioned context artifacts, an externalized memory bank, and
LLM-as-judge evals — aimed at the bloated-context failure mode coding agents
hit more often than a missing capability.

Prior update: Compaction picked up a documented **safety** failure mode: "Governance
Decay" shows that context summarization/eviction in long-running agents can
silently erase the safety and governance constraints set earlier in the
session, reframing the compactor as a security-critical layer that needs
constraint-preserving guarantees — not just a token-saving one.

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
