---
slug: agent-memory
kind: obstacle
title: "Agents forget across steps and sessions"
area: memory
status: active
solutions: [vector-kb, context-compaction]
obstacles: []
related_storylines: []
evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44, 23f07233dca1a9dc, a026d7598baf3bcf, 495bc8d2b48db179, 8688a4c832b1b52a, f42a28fa00ccf0ea, 246a4c93052ef3c1, a100d2bc462a761c, 56ef11c9d3f8e424, b07c69459b16cc11, dc1acd837d32b604, 8561672eafb892cc, 1609e44adca88f23, 27401e60c46c5950, fae52c3b17c1c504, 7b8e28ef4195d912, d5702ff0cbee7342, 6e834d3516003b88, d7f7f1bf25c4ce76, 7339a1b37836ee76, ffff9fe41413e4ac, 6025c4e3bc9c120a, 34c069f2bffc49df, 5ba78b757300e8cc, 474ba1f9a89fdca5, 40602cd71e370eb6, 5a50cd46503b235d, 34691d4d3bab21f8, afd8d930f6a32d8c, 5f608b2d21b1899e, b87db2b7c0188c42, 839b8e795fbb51a0, ed614d89952e3d29, 6d2d70e4ee226dfc, 5960e24b491051f2, 92250613f04ac1b9, c95ec4fda28e63d4, cdd1118267ee925c, bfa81ecf238132fd, d520b85be68f5411]
updated: 2026-09-03
covers_evidence: [2c8ff757b828dee7, 9022c498f1c24442, b3b803dc3d3ab1b8, 5c5003b8c444211d, 623de2bad771dca8, f472926ede32221b, f6cf006fbdea0d5a, eb5267262e7d31c8, cc131dd2666136ca, fbb59a181d9a71e6, 0657f60e37a5d3d2, ce180fd0b3a2065e, a44d7493026627ec, a803b4966933291a, ca2de3ecb9f0eb55, c7a2ede639a1a707, ee624f89c3319a44, 23f07233dca1a9dc, a026d7598baf3bcf, 495bc8d2b48db179, 8688a4c832b1b52a, f42a28fa00ccf0ea, 246a4c93052ef3c1, a100d2bc462a761c, 56ef11c9d3f8e424, b07c69459b16cc11, dc1acd837d32b604, 8561672eafb892cc, 1609e44adca88f23, 27401e60c46c5950, fae52c3b17c1c504, 7b8e28ef4195d912, d5702ff0cbee7342, 6e834d3516003b88, d7f7f1bf25c4ce76, 7339a1b37836ee76, ffff9fe41413e4ac, 6025c4e3bc9c120a, 34c069f2bffc49df, 5ba78b757300e8cc, 474ba1f9a89fdca5, 40602cd71e370eb6, 5a50cd46503b235d, 34691d4d3bab21f8, afd8d930f6a32d8c, 5f608b2d21b1899e, b87db2b7c0188c42, 839b8e795fbb51a0, ed614d89952e3d29, 6d2d70e4ee226dfc, 5960e24b491051f2, 92250613f04ac1b9, c95ec4fda28e63d4, cdd1118267ee925c, bfa81ecf238132fd, d520b85be68f5411]
---

## TL;DR
An agent's working memory is its context window, which is finite and resets
between runs. On long-horizon tasks it forgets earlier steps, repeats work, and
loses the user's intent — so "agent memory" (what to persist, where, and how to
recall it) becomes a first-class architecture problem rather than a prompt tweak.

## State of the art
The field has converged on **memory as a tiered system** rather than a single
store: short-term/working memory (the live context window), episodic memory
(a log of past interactions), and long-term/semantic memory (durable facts
and preferences). LinkedIn's cognitive-memory writeup frames this split
explicitly and is a useful reference architecture.

The tiered model now has an open, **production-grade instance**: Elastic's
Atlas implements three memory categories on top of Elasticsearch (infra many
teams already run), exposes them to agents over [MCP](/topic/mcp), keeps
per-user memory isolated, and reports evaluation numbers rather than a demo —
pushing "cognitive memory" from reference diagram to shippable component.
Practitioners read this as memory *leaving the "remember this" demo phase*
and becoming a real engineering layer.

The hard questions are no longer "should the agent have memory" but **what
to write, when to write it, and how to recall the right slice cheaply** —
which is where the two linked solutions diverge: retrieval from an external
store (vector/graph knowledge bases) versus keeping the working set small via
compaction.

A broader framing argues the tiered-store model above is still too narrow:
"Agentic Context Management" (ACM) treats memory as a **lifecycle, not a
store** — deciding what to remember, extracting and structuring it, choosing
the right store per data type, consolidating and forgetting while preserving
provenance, judging what's relevant now, anticipating what's needed next, and
compacting to a token budget without losing what matters, all across an
organization's scope hierarchy rather than a single user. The paper names
five primitives (architecting, ingesting, scoping, anticipating, compacting &
consolidation) and ships a reference implementation, Maximem Synap. It also
puts a number on why compaction quality matters: naive context accumulation
grows token cost quadratically in conversation length, crude summarization
buys linear cost at the price of an accuracy cliff, and only validated
compaction achieves linear cost with fidelity preserved — the cost curve this
page's tiered/compaction split has been assuming without naming (see
[agent cost](/topic/agent-cost) for the run-time consequence).

Recall itself is getting scrutinized: "Root Memories" shows similarity-based
retrieval misses memories that are *logically* relevant rather than
lexically close to the query, so the recall step has to reason over what's
stored, not just embed-and-rank (see
[vector/graph retrieval](/topic/vector-kb)).

The market is splitting along a **build-vs-buy** seam: managed offerings
(e.g. Cloudflare's persistent Agent Memory service) move memory toward
buy-able infrastructure, while a parallel wave of local-first, single-file,
developer-owned stores treats memory as a component you install and own
rather than a service you rent:

- bi-temporal memory in one SQLite file (Memharness)
- local-first encrypted memory over MCP (Cortex)
- curated file-based project memory (Brain2.0)
- graph-based associative memory built with ~zero LLM calls (FERNme)
- deterministic memory paired with agent guardrails in one package (OpenLore)
- zero-dependency memory in a single SQLite file, no infrastructure to run (Remembrane)

As that wave matures the question shifts from "where does memory live" to
**"how does it follow the agent"**: a durable, S3-backed filesystem that
mounts the same memory markdowns across a laptop and the cloud treats the
store as a *portable substrate* you sync between runtimes rather than a
per-platform silo — the build-it-yourself answer to the cross-platform
consistency that managed services sell.

The same portability instinct now extends to **sharing memory across
agents, not just across runtimes**: Sibyl is a self-hosted, multi-user
memory system (built on SurrealDB) that many parallel coding agents on the
same machine or team read and write through a CLI or MCP, reporting 96.96%
strict recall@5 on LongMemEval-S with no LLM in the retrieval path —
evidence that a shared, developer-owned memory substrate can both scale to
many concurrent agents and stay cheap to query.

A recurring design theme in this wave is **richer temporal modeling**:
bi-temporal stores track both when a fact was true and when the agent
learned it, so recall can reason about staleness instead of returning
whatever embeds nearest.

TEPA gives that staleness problem a concrete mechanism and a number: it
represents each memory as a keyed precedent and revokes the active one the
moment fresher evidence contradicts the same key, instead of letting old
and new facts coexist in the retrieval set. Under full reversal, both
append-only and last-write-wins caches score *below* having no memory at
all (0.210 vs. 0.309), while TEPA's revocation holds accuracy at 0.950 —
direct evidence that a memory system without revocation isn't neutral on
stale facts, it actively makes an agent worse than not remembering.

A second, cost-driven theme is **cheap, mechanical writes**: rather than
calling an LLM to decide what to store, newer stores build the memory
structure deterministically — FERNme forms associative memory tags from
fuzzy edges and a Hebbian co-occurrence rule, and local-first stores like PMB
index writes with a hybrid BM25-plus-vector retriever in a single SQLite
file — so persisting and recalling what an agent learns stops being a
per-turn token bill.

A third, newer theme is **memory integrity**: persistent memory is also a
persistent attack surface. A reproducible benchmark shows agent-memory
systems readily admit *poisoned facts* — adversarial or wrong entries that
get written once and then retrieved as trusted context on every later turn —
which makes write-time validation and provenance, not just recall quality,
part of the memory-engineering job (and ties memory to
[prompt injection](/topic/prompt-injection)).

Integrity is one slice of a broader move to **make memory quality
measurable**: a dedicated benchmark for the *failure modes* of agent memory
— not just poisoning but forgetting, stale recall, and retrieval that
returns the wrong slice — turns "did the memory layer help" into a number
you can regress on, the same trajectory evaluation took
([agent benchmarks](/topic/agent-benchmarks)).

Underneath the architecture debate the practitioner consensus is also
consolidating: vendor guides now lay out the same tiered split (short-term
context plus durable long-term store) as settled practice and add a feedback
loop on top — analyze the agent's own *traces* to decide what is worth
remembering and to let it improve across runs — so memory is increasingly
framed as something the agent curates from its own history, not just a
place facts are dumped.

The local-first wave keeps widening: **Knotic** layers memory into
project/session/docs tiers for coding agents specifically, matching the
tiered-memory reference architecture at the single-developer scale rather
than the enterprise one — the same split showing up bottom-up as well as
top-down.

A second, sharper way to fix context rot is emerging alongside compaction:
**recursive dispatch**. LangChain's recursive-language-model (RLM) pattern
in Deep Agents has the agent write code that dispatches sub-agents over
*chunks* of context instead of pumping the whole history into one window —
trading a single long-context call for many short-context ones, which sidesteps
context rot rather than compressing around it (see
[context compaction](/topic/context-compaction) for the compress-in-place
alternative).

Memory integrity's failure surface just grew a new axis: **sycophancy**.
MemSyco-Bench shows that retrieved memories don't just risk being wrong
(poisoned facts) — they can be *directionally* wrong, reinforcing whatever
the user or a past turn wanted to hear rather than what's true, which is a
harder failure to catch than an outright false fact because it looks like
the memory system working as intended. Formal testbeds for the underlying
contract are also arriving: AgenticSTS frames long-horizon agent memory as
"a contract about what each future decision is allowed to see," giving the
poisoning/sycophancy/forgetting failure modes a shared bounded-memory
benchmark to run against.

Memory integrity's threat model now has a **stealthier** entrant than
outright poisoning: persistent personal agents can be made to remember an
injected instruction but never surface it to the user, so the agent quietly
acts on the planted memory in the background while looking normal in the
foreground conversation — a variant that write-time validation aimed at
catching an obviously wrong or poisoned fact won't necessarily flag, because
nothing about the entry looks false, only concealed.

The architecture debate now also has a **brute-force alternative** at the
model layer: Claude Code shipping Sonnet 5 as its default with a native
1M-token context window (at $2/$10 per Mtok promotional pricing) means some
long-horizon tasks can skip compaction and retrieval entirely by just fitting
more raw history in-window — shrinking, not eliminating, the set of tasks
where the tiered-memory engineering above is required. A practitioner
benchmark now backs that claim with a measured long-horizon run rather than
a token-limit spec sheet: a single agent session pushed through all 89
sequential Terminal-Bench 2.0 tasks back to back — over 80 million tokens —
with no compaction and no measurable accuracy loss versus giving each task
its own fresh session, direct evidence that "just extend the window" holds
up across a real multi-task benchmark, not only a synthetic long-context
probe.

That "just extend the window" argument now has a direct rebuttal from the
local-first camp: a continuity protocol argues explicitly that 1M-token
context windows don't solve agent memory, since a longer window is still
discarded between sessions and still degrades under context rot within a
single long run — a protocol, not a bigger window, is what closes the gap.
It's the same tiered-vs-brute-force fault line this page already tracks,
argued from the side that a longer context is orthogonal to durable memory,
not a substitute for it.

The local-first, developer-owned roster keeps growing: MemHub adds
persistent shared memory for coding agents, and Hugging Face's Funes
project makes the "own your memory, don't rent it" pitch explicit in its
title — both extending the local-first wave (Memharness, Cortex, Brain2.0,
Sibyl) already on this page. A companion production-architecture talk backs
the tiered-store consensus with a concrete stack: Redis for short- and
long-term memory, summarization to manage token limits, and reranking plus
semantic caching to fight context rot under latency constraints — the same
tiered split this page already tracks, this time named down to the specific
infrastructure a team would actually run.

The MCP-as-transport pattern for memory keeps spreading to narrower,
developer-facing stores: codebase-memory-mcp exposes a codebase's own
memory (prior findings, decisions, file context) to coding agents over MCP,
the same "memory over MCP" shape as Atlas but scoped to one repo instead of
an enterprise platform.

The measurability push above now has a public leaderboard, not just a
benchmark paper: the Agent Memory Leaderboard released its first public
results for **text memory** specifically, scoring open-source methods
against commercial products head-to-head with 136 teams registered — moving
memory evaluation from a one-off benchmark citation toward a maintained,
comparable ranking, the way [agent benchmarks](/topic/agent-benchmarks)
already work for general agent capability.

A parallel model widens the source side of proactive memory rather than the
storage side: OpenWiki Brains turns Gmail, Notion, git repos, X, Hacker News,
and web search into a local wiki of plain Markdown files an agent can pull
from without being told to remember — proactive recall instead of the
mostly-reactive "remember this" pattern most assistants still ship, and an
architecture (synthesized markdown as the durable memory layer, refreshed by
scheduled jobs rather than a vector index) that mirrors the LLM-wiki pattern
this site's own knowledge wiki uses.

A companion release from the same lab turns the OpenWiki concept toward
**integrity rather than sourcing**: its self-correcting memory layer stores
evidence-backed claims rather than raw facts, uses that evidence to detect
when a claim has gone stale as the underlying codebase evolves, and corrects
or drops it instead of retrieving whatever was written last — a write-time
defense against the poisoning and staleness failure modes this page already
tracks, pointed specifically at codebase memory.

The integrity threat model keeps widening past the entry itself to the
agent's own reasoning: a new benchmark targets forged-reasoning attacks,
where an agent's stored reasoning history — not just a stored fact — can be
adversarially manipulated, extending memory poisoning from corrupting what
the agent believes to corrupting how it argues for it.

**Coordination between agents writing to shared memory** gets a low-tech
answer: rather than a purpose-built memory service, a production pattern
uses Postgres's own ACID transactions and row-level locking so multiple
agents can write shared notes and decisions without conflicting — a "cheap
and dirty work queue" built on the concurrency control a relational database
already provides, not a new memory primitive. It's the same "ride
infrastructure you already run" instinct as Elastic's Atlas and BetterDB
above, applied to the write-conflict problem specifically rather than to
retrieval.

The local-first wave's "one brain across every client" instinct gets a
concrete, sub-second-recall implementation: CMEM pairs a local SQLite store
of timestamped observations (decisions, dead ends, fixes — not just diffs)
with a built-in vector index for semantic recall, exposes both to any
MCP-speaking client through a single server so Cursor, Claude Code, and a
bare CLI agent share the same memory, and reports recall under one second.
It ships 11 bundled skills so a team doesn't have to build the write/recall
logic itself (the vendor cites 6+ weeks of engineering for a custom
equivalent), runs fully self-hosted and open-source (Apache-2.0) with an
optional paid cloud mirror for cross-device sync — the same
buy-vs-build-and-self-host split this page's local-first tier already
tracks (Memharness, Cortex, Brain2.0), this time bundling the MCP transport
and the skills on top of the store itself.

A **programmatic memory** approach answers the retrieval-vs-context tradeoff
from a third direction: PRO-LONG keeps a complete, structured interaction log
rather than summarizing or pruning it, and uses a coding agent to search that
log programmatically instead of embedding-and-ranking it. On the full
ARC-AGI-3 public game set it improves 18.0 percentage points over a base
coding agent and matches or beats specialized long-horizon harnesses (up to
76.1% pass@1) while using 4.2-5.8x fewer tokens — treating memory retrieval
as a code-search problem rather than a vector-similarity one.

A narrower failure mode targets **repair reuse** specifically: LLM agents
that fix a failure and move on typically discard the successful correction,
so a later episode facing the same underlying bug has to rediscover the fix
from scratch instead of recalling it. Causal episodic memory keeps the
finalized repair outcome — not just the fact it happened, but the causal
link between the failure and what fixed it — and reuses it on later
Text-to-SQL episodes that hit the same class of error, treating "what
worked last time" as its own memory object distinct from facts or
preferences (see [context compaction](/topic/context-compaction) for the
adjacent question of what to keep in-window versus persist).

A distinct failure mode shows up on the **write side** rather than recall:
persistent instruction files like `CLAUDE.md` grow without bound in real
repositories, stopping only when the repo retires or someone rewrites the
file wholesale. The mechanism is imperfect recall, not poisoning or
staleness — an agent appends a new instruction because it can't reliably
tell whether an equivalent one is already there, so the file accumulates
redundant and conflicting guidance instead of being edited in place.
"Catastrophic Remembering" names the pattern directly: unlike the retrieval
and revocation failures above, this is a curation failure in a store that
has no retrieval step at all — the whole file is read every turn — so the
fix has to be write-time deduplication and pruning, not a better recall
mechanism.

A practitioner talk ties the tiered-store and compaction threads above
directly to a **build discipline**, not just an architecture diagram: "The
Right 300 Tokens Beat 100k Noisy Ones" argues coding agents fail from
bloated, stuffed context rather than a missing capability, and names the
concrete fixes — lazy-loaded skills (load a skill's instructions only when
the task needs them, not every turn), versioned context artifacts, an
externalized memory bank, and LLM-as-judge evals — as the practical
counterpart to this page's lifecycle and tiered-store framing (ACM, Atlas)
above, aimed at engineering leaders turning raw markdown files into reliable
agentic workflows rather than at the memory-architecture literature itself.

A companion question to the tiered-store and lifecycle debates above asks
**how much memory an agent needs at all**, not just where it lives or how
it's structured: IBM Research's ALTK work frames memory sizing as its own
hierarchical-memory-management design question, distinct from the
store-choice and staleness questions this page already tracks.

A companion question to the "how much memory" debate above targets *quality*
rather than volume. **Memory failure modes now have a benchmark that isn't
just poisoning**: MemTrapBench evaluates whether a model's memory use falls
into cognitive traps — retaining information correctly is necessary but not
sufficient if the model still reasons about it in a biased or trap-prone
way — widening the measurability push (Agent Memory Leaderboard, the
failure-modes benchmark) into reasoning-over-memory quality, not just recall
accuracy. A narrower architecture entrant answers the low-density,
long-horizon case specifically: FTA-Mem anchors memory to fact, time, and
affect for emotional-support agents, where turns are incomplete and
evidence is scattered across a long relationship rather than one dense
session. And CABLE names a recall failure distinct from poisoning or
staleness: an agent can fail to recover relevant evidence through a bounded
context interface even when the fact was stored correctly earlier, arguing
the interface itself — not just the store — limits what later steps can
retrieve (cross-ref [grounding](/topic/grounding) for the retrieval-quality
side of the same gap).

A **recursive self-improvement** approach targets the same long-horizon
failure "The Right 300 Tokens" and PRO-LONG above address from a training
angle rather than a retrieval or code-search one: Recuris pairs a working
memory (tracks task progress, guides skill selection) with an experiential
memory (stores reusable skills), and a meta-agent that makes localized,
validation-gated edits to the skill store after each failure — a bounded
loop where accumulated experience reshapes the agent's own behavior instead
of only its context. Across 37 model-benchmark pairs it improves 35, gains
widen to +32.2 points on the longest-horizon tasks tested, and long-horizon
failures drop by up to 80%, evidence that skill-memory evolution keeps
paying off precisely where compaction and retrieval both get harder — the
longer the run.

The **zero-LLM-retrieval, local-first pattern** (Sibyl, PMB above) gets
another concrete instance with a full benchmark breakdown: Awareness Local
stores memories as git-compatible Markdown, indexes them with SQLite FTS5
plus optional local embeddings, and retrieves via hybrid BM25-plus-vector
reciprocal rank fusion with no LLM in the loop — reporting 96.0% recall@5
on LongMemEval (ICLR 2025), in the same recall range Sibyl reported on the
same benchmark, evidence that the hybrid-retrieval-no-LLM recipe is
converging into a repeatable pattern rather than one team's result.

The local-first coding-agent memory wave picked up three more entrants in a
single week: OpenContext (project-local memory over MCP) and Contextual
(local codebase memory) join the existing local-first roster, while Memctl
answers this page's own "Catastrophic Remembering" problem directly —
git-style versioning, diffing, and rollback for the persistent instruction
files (`CLAUDE.md`/`AGENTS.md`) that otherwise accumulate redundant,
conflicting guidance with no way to undo a bad edit. A companion postmortem
grounds the failure side in a concrete incident rather than a benchmark:
an autonomous coding agent left unattended for hours accumulated memory
bugs that only surfaced once nobody was watching the session live —
evidence that the write-side curation failures this page tracks compound
specifically in long, unsupervised runs, not just long conversations.

The measurability push above (Agent Memory Leaderboard) now has a benchmark
that targets *using* retrieved memory, not just recovering it: UTILMEM finds
that strong scores on conventional factual-recall benchmarks don't reliably
predict **memory utilization** — reasoning over dense histories, catching
implicitly relevant memories, synthesizing evidence scattered across
sessions, and resisting semantically similar distractors — and that even
when a system successfully retrieves the right evidence, it often still
fails to integrate it or gets misled by a plausible-looking distractor. It
sharpens this page's standing "retrieval alone is insufficient" argument
(see [grounding](/topic/grounding) for the retrieval-quality side) into a
named, separately-scored capability. A production-shaped answer to the same
gap arrives from the provenance-and-integrity side: Agent Zero Memory splits
a user's history into three parallel systems — an episodic timeline, an
entity-event knowledge graph, and a citation-locked semantic store of
durable facts — and enforces a **citation lock** that only lets an answer
cite evidence it actually retrieved, so fabrication is structurally excluded
and the system abstains instead of guessing when it isn't sure. It's a
stricter, provenance-first answer to the poisoning and integrity failure
modes this page already tracks, built into the retrieval contract itself
rather than checked after the fact.

## What's new
A continuity protocol directly rebuts the "just extend the window" argument
this page already tracks: it argues 1M-token context windows don't solve
agent memory, since a bigger window is still discarded between sessions and
still degrades under context rot within one long run, and ships a protocol
instead of a longer window as the fix (see State of the art above).

Prior update: UTILMEM finds that strong scores on conventional factual-recall memory
benchmarks don't reliably predict **memory utilization** — reasoning over
dense histories, catching implicitly relevant memories, and resisting
distractors — sharpening this page's "retrieval alone is insufficient"
argument into a named, separately-scored capability. Agent Zero Memory
answers the integrity side with a **citation lock**: an answer may only cite
evidence it actually retrieved, structurally excluding fabrication rather
than checking for it after the fact (see State of the art above).

Prior update: Three more local-first coding-agent memory tools shipped in one week
(OpenContext, Contextual, Memctl), with Memctl specifically answering this
page's "Catastrophic Remembering" problem — git-style versioning and
rollback for `CLAUDE.md`/`AGENTS.md` instead of unbounded, undeduplicated
growth. A companion postmortem shows the same write-side failure surfacing
in an autonomous coding agent left unattended for hours.

## Why it matters for platform engineers
Memory is where agent cost, latency, and reliability collide: stuffing
everything into context is simple but blows up token cost and latency and still
forgets; an external store adds a retrieval hop and a freshness/consistency
problem. The decision (compact vs. retrieve vs. both, build vs. buy) is an
infrastructure decision with an ongoing operational tail — eviction policies,
index maintenance, and recall evaluation — not a one-time integration.
