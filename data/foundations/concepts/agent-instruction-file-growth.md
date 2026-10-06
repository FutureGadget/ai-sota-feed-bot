---
slug: agent-instruction-file-growth
title: "Why does CLAUDE.md (or AGENTS.md) only ever grow, never shrink?"
question: "Why does CLAUDE.md (or AGENTS.md) only ever grow, never shrink?"
summary: "Agent instruction files grow because appending a rule is cheap while proving a rule is safe to delete becomes combinatorial once its rationale is forgotten. A 1,867-repository study found these files more than tripling; writing the why next to each rule reversed the growth."
status: active
cluster: memory
updated: 2026-10-06
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [agent-memory, context-compaction]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: chakrabarti-2026-catastrophic-remembering-theory
    kind: theory-paper
    title: "Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"
    url: "http://arxiv.org/abs/2608.11095"
    added: 2026-08-15
    note: "Names 'catastrophic remembering', the inverse of catastrophic forgetting, and traces it to a cost asymmetry. Appending an instruction to a prompt of |D| instructions is O(1). Once the rationale is lost, proving a deletion causes no regression costs O(2^|D|) in the worst case, because the instruction can interact with any subset of the others. Single-author preprint (submitted 2026-08-11), not yet independently replicated."
  - id: chakrabarti-2026-catastrophic-remembering-benchmark
    kind: benchmark-result
    title: "Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"
    url: "http://arxiv.org/abs/2608.11095"
    sid: "ffff9fe41413e4ac"
    added: 2026-08-15
    note: "Tracks 247,694 instruction lifetimes in 1,867 repositories: instruction files grow +226% over their lifetime, +4.9 net instructions per commit, and deletion hazard falls with age (log-hazard -0.032/commit). In synthetic 'verifiable worlds' built by inverting IFEval, rationale comments cut excess instructions from +211.3% to +1.4% (a 99.3% reduction) and improved WildIFEval instruction-following by up to 23.1%. Single-author preprint; numbers not yet independently replicated."
  - id: agent-instruction-file-growth-editorial-synthesis
    kind: editorial-inference
    title: "Single-paper caveat and relation to session context growth"
    added: 2026-08-15
    note: "Editorial synthesis: the cost-asymmetry mechanism and the direction of the fix are worth acting on before replication; treat the exact percentages as one paper's figures. This differs from agent-context-lifecycle, which covers a live session's context cost growing turn by turn. Here a persistent instruction file grows across commit history because deletions become unverifiable once a rule's reason is lost."
---

## Builder consequence
If your CLAUDE.md, AGENTS.md, or system prompt only gains rules, trying harder to prune will not fix it. The cause is a cost asymmetry: once nobody remembers why a rule was added, proving it is safe to remove becomes a combinatorial check nobody runs. A 1,867-repository study found these files more than tripling. The fix is changing what you write when you add a rule.

## Short answer
Appending an instruction costs one line. Safely deleting one requires proving it will not reintroduce the failure it was added to prevent. Once that reason is forgotten, the proof means reasoning about how the instruction interacts with every other instruction in the file, a cost that grows exponentially with file size. Nobody pays it, so the file only grows. Writing the rationale as a comment next to each rule is the one intervention shown to reverse this.

## Builder model
Model an instruction file as an append-only log with hidden debt, not a document you tidy now and then. Every rule added without its *why* is a future deletion decision that gets more expensive as the file grows. "Clean sweep" rewrites reset the size but not the asymmetry, so growth resumes on the next commit. The fix has to change the cost of deletion, not the current size.

## Mechanism
**Append is cheap; verified delete is exponential.** Adding instruction `|D|+1` is O(1). Removing an old instruction whose purpose is lost means checking whether any subset of the other instructions depends on it, which is O(2^|D|) in the worst case. The rational default becomes "leave it in."

**Real repositories show the signature.** The catastrophic-remembering study tracked 247,694 instruction lifetimes and found files growing +226% over their lifetime, adding a net +4.9 instructions per commit. The older an instruction is, the less likely anyone removes it.

**The bottleneck is the missing rationale, not the count.** A comment stating what an instruction guards against turns "why is this here" from a reconstruction-by-testing problem into a fact you can read and re-check. In the paper's controlled test, rationale comments cut excess instructions from +211.3% to +1.4% over the known-optimal set and improved real-world instruction-following by up to 23.1%. The comments change whether the agent follows instructions correctly, not just file size.

**It generalizes beyond CLAUDE.md.** Any accreting instruction surface an agent or team treats as authoritative, such as system prompts, runbooks, or review checklists, has the same asymmetry.

## Math intuition
"Safe to delete" means checking instruction A's effect across every combination of the other instructions still present, because instruction B might only matter *because* A exists. A set of size `n` has `2^n` subsets, so the check grows exponentially:

- 10 instructions: 1,024 combinations.
- 30 instructions: over a billion.

Neither a person nor an agent can run that check without a stated reason for each instruction. A rationale comment replaces the exponential search over hidden interactions with a linear read of stated dependencies: for each rule, is the reason it was added still true?

## How to apply
- **Write the why next to every new rule** in CLAUDE.md, AGENTS.md, or a system prompt: the failure it prevents or the constraint it enforces. Brevity and better organization were not the measured fix; rationale comments were.
- **Delete rules whose stated reason is stale first.** A documented rationale turns a combinatorial guess into one fact-check.
- **Track net instructions added per commit** on any file agents read as instructions. Steady upward drift with no deletions is the growth signature.
- **Treat old, undocumented rules as your highest-risk debt.** Deletion likelihood falls with age, so the longer an unexplained rule survives, the less likely it is ever reconsidered.
- **Do not rely on periodic clean-sweep rewrites.** Without rationale comments, growth resumes immediately.

## Failure modes
- Deleting an old, undocumented rule on a hunch, triggering the regression it silently prevented and making the team afraid to delete anything again.
- Fixing for shorter instructions instead of documented reasons.
- Assuming the problem is specific to CLAUDE.md when any accreting instruction surface has it.
- Citing the 99.3% bloat reduction or 23.1% gain as replicated results rather than one preprint's figures.
- Confusing this with session context bloat: this is a persistent file growing across commits, not a conversation growing turn by turn.

## Related
See [agent memory](/topic/agent-memory) for how agents retain and lose information, and [context compaction](/topic/context-compaction) for shrinking context without losing what matters. `agent-context-lifecycle` covers the sibling problem of a single session's context cost growing quadratically.
