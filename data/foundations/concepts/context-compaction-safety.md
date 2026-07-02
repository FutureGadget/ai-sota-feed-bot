---
slug: context-compaction-safety
title: "Does compacting an agent's context put its safety rules at risk?"
question: "Does compacting an agent's context put its safety rules at risk?"
summary: "Context compaction is not just a lossy cost optimization — a 1,323-episode benchmark shows it can silently erase the governance constraints a long-running agent was given, and only pinning those constraints outside the compactible window prevents it."
status: active
cluster: safety
updated: 2026-07-02
audience: "strong-software-engineer"
related_topics: [context-compaction, agent-memory, prompt-injection]
related_playbook_cards: [pb-pin-governance-constraints-past-compaction, pb-close-the-trace-to-memory-loop]
related_storylines: []
evidence:
  - id: constraintrot-2026-governance-decay
    kind: benchmark-result
    title: "Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents"
    url: "http://arxiv.org/abs/2606.22528v1"
    note: "ConstraintRot benchmark, 1,323 episodes across seven model families: prohibited-action violation is 0% with the policy in full context, rises to 30% after ordinary compaction (up to 59% for some models), stays 0% when the constraint survives the summary, and reaches 38% when it is dropped. A Compaction-Eviction Attack (adversarial content that biases the summarizer to drop the policy) defeats every evaluated model; the paper's training-free Constraint Pinning mitigation restores violation to 0%."
  - id: langchain-2026-agent-memory-guide
    kind: primary-doc
    title: "How to Build Memory into AI Agents"
    url: "https://www.langchain.com/blog/how-to-give-your-agent-memory"
    note: "Frames agent memory as short-term (live context), episodic, and long-term/semantic tiers, and recommends a capture-traces -> analyze -> selectively-update loop over long-term memory rather than dumping raw history into it."
  - id: elastic-atlas-2026-cognitive-memory
    kind: production-field-report
    title: "Elastic Open-Sources Atlas Agent Memory Based on Cognitive Science"
    url: "https://www.infoq.com/news/2026/06/elastic-atlas-agent-memory/"
    note: "Elastic's Atlas ships three memory categories on Elasticsearch, exposed to agents over MCP with per-user isolation, and reports 0.89 Recall@10 on a question-answering evaluation rather than shipping the architecture as an unverified diagram."
  - id: context-compaction-safety-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "For agent builders, any lossy transform in the memory pipeline (compaction, retrieval, forgetting) is a place a safety-relevant fact can silently vanish, and it needs the same adversarial testing discipline as prompt injection, not just a happy-path check."
covers_evidence:
  - constraintrot-2026-governance-decay
  - langchain-2026-agent-memory-guide
  - elastic-atlas-2026-cognitive-memory
  - context-compaction-safety-editorial-synthesis
---

## Builder consequence
If your agent runs long enough to need context compaction — summarizing, evicting, or compressing older turns to stay under a token budget — the compactor is not a neutral cost optimization. It is a place where the rules you gave the agent up front (forbidden tools, approval gates, a user's hard "do not") can silently disappear. The agent will keep acting exactly as if nothing changed, because from its perspective nothing did: the constraint is simply no longer in what it can see.

## Short answer
Context compaction can silently erase safety and governance constraints stated earlier in a long-running session, and this is not a rare edge case: across 1,323 episodes and seven model families, prohibited-action violation rises from 0% with the constraint in full context to 30% after ordinary compaction, and as high as 59% for some models. When the constraint text survives the summary, violations stay at 0%. The fix isn't "compact less" — it's "never let the compaction step touch the parts of context that carry hard rules."

## Builder model
Split what lives in an agent's context into two classes: content that can be safely lost and re-derived (task history, intermediate reasoning, prior tool outputs) and content that is load-bearing and irreversible if lost (permissions, forbidden actions, hard constraints, approval gates). Ordinary summarization treats both classes the same way — it compresses for information density, not for which sentence is a safety rule. Once a governance constraint gets paraphrased away or dropped for space, the agent isn't disobeying a rule it still holds; it genuinely no longer has the rule in front of it. The same threat model as prompt injection applies to your own compactor: an untrusted or adversarial step in the pipeline can remove instructions you rely on, whether by accident or on purpose.

## Mechanism
A long-horizon agent keeps a token budget. To stay under it, agents typically evict old turns, replace them with a running summary, or roll both together — a summarization model or heuristic decides what to keep, usually optimizing for task continuity, not rule preservation.

The Governance Decay study measures how often a stated policy constraint survives this process, using ConstraintRot, a benchmark of long-horizon agent scenarios with deterministic tool-call grading. The results:

- **0% violation** when the constraint sits in full, uncompacted context
- **30% violation** after ordinary compaction (up to 59% for some models)
- **0% violation** when the compacted summary happens to retain the constraint's wording
- **38% violation** when the wording is dropped

The paper also demonstrates a Compaction-Eviction Attack: adversarial in-context content crafted to bias the summarizer toward omitting a legitimate policy. Optimized versions of this attack defeat every model they evaluate, turning the compactor into an active adversarial target, not just a source of accidental loss.

Their proposed fix, Constraint Pinning, is training-free: it quarantines governance constraints so the compaction step can't touch them. That alone restores violation to 0% in their benchmark.

This mechanism generalizes beyond safety text. The tiered memory architecture practitioners converge on — short-term working context, episodic history, long-term semantic store — moves information through a lossy transform at every tier: summarize, embed-and-retrieve, or forget. None of those transforms natively distinguishes a detail that no longer matters from a detail the system depends on.

## Evidence
- Benchmark/result-backed: Governance Decay / ConstraintRot measures constraint-violation rate across 1,323 episodes and seven model families: 0% with the policy in full context, 30% after ordinary compaction (up to 59% for some models), 0% when the constraint survives the summary, 38% when it's dropped; a Compaction-Eviction Attack defeats every evaluated model, and training-free Constraint Pinning restores violation to 0%.
- Primary-doc-backed: LangChain's practitioner guide frames agent memory as short-term (live context), episodic, and long-term/semantic tiers, and recommends a capture -> analyze -> update loop over trace data instead of dumping raw history into long-term memory.
- Production field-report-backed: Elastic's Atlas ships three memory categories on top of Elasticsearch, exposed to agents over MCP with per-user isolation, and reports a measured evaluation number (0.89 Recall@10) rather than shipping the architecture as an unverified diagram — the same discipline this concept asks builders to apply to compaction specifically.
- Editorial inference: treat any lossy transform in the memory pipeline as a place a safety-relevant fact can silently vanish, and test for it adversarially, not just on the happy path.

## How to apply
Four changes close this gap:

- **Pin hard constraints outside the compactible window.** Identify every rule your agent depends on (forbidden tools, approval gates, hard user "do nots", compliance rules), store them in a pinned system block your summarization step cannot rewrite or evict, and re-inject the verbatim text into every post-compaction prompt instead of trusting the running summary to carry it forward.
- **Add a compaction regression test.** Force a compaction cycle mid-session, then attempt the prohibited action and assert the agent still refuses. The check is cheap and training-free, but only catches the failure if you actually run it — governance decay is invisible until you specifically probe for it.
- **Treat the compactor as untrusted input.** If an attacker can influence what enters context (a tool response, a retrieved document), assume they can bias the summarizer into dropping a constraint the same way they'd exploit an injected tool result. Make sure the pinned region cannot be edited by anything the compactor reads.
- **Require a measured number from any memory architecture.** Whether it's a tiered store, external retrieval, or a vendor-shipped memory service, demand an evaluation number before you trust an unverified "we added memory" claim.

## Failure modes
- Compaction as a black box: trusting a summarizer to preserve "the important parts" without testing whether governance-relevant text specifically survives.
- Treating governance decay as rare: benchmark data says otherwise — violation rates hit double digits under ordinary compaction, not just adversarial conditions.
- No adversarial test: never running a Compaction-Eviction-style attack against your own pipeline, so the first adversarial constraint drop happens in production.
- Same-tier assumption: managing safety rules and disposable task history with the same lossy pipeline instead of splitting load-bearing content into a pinned, non-evictable region.
- Shipping memory without an eval number: adding a memory layer (compaction, retrieval, or a vendor service) and calling it done without measuring whether it actually preserves what matters.

## Related
See [context compaction](/topic/context-compaction) for compaction techniques and their cost/latency trade-offs, [agent memory](/topic/agent-memory) for the broader tiered-memory architecture debate, and [prompt injection](/topic/prompt-injection) for the adjacent threat model where untrusted content hijacks what an agent trusts.
