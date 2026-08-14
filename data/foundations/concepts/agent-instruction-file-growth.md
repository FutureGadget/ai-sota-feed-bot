---
slug: agent-instruction-file-growth
title: "Why does CLAUDE.md (or AGENTS.md) only ever grow, never shrink?"
question: "Why does CLAUDE.md (or AGENTS.md) only ever grow, never shrink?"
summary: "Agent instruction files grow because appending a rule is cheap while proving a rule is safe to delete becomes combinatorial once its rationale is forgotten — a 1,867-repository study found these files more than tripling over their lifetime, and encoding the *why* next to each rule is the one intervention shown to reverse the growth."
status: active
cluster: memory
updated: 2026-08-14
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
    note: "Names the phenomenon 'catastrophic remembering' (the inverse of catastrophic forgetting) and traces it to a cost asymmetry: appending an instruction to a prompt of |D| instructions is O(1), but once an instruction's rationale is gone, verifying that removing it won't cause a correctness regression costs O(2^|D|) in the worst case, because the instruction can interact with any subset of the others."
  - id: chakrabarti-2026-catastrophic-remembering-benchmark
    kind: benchmark-result
    title: "Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"
    url: "http://arxiv.org/abs/2608.11095"
    note: "Measures the phenomenon across 247,694 instruction lifetimes in 1,867 repositories: agentic instruction files grow more than tripling over their lifetime (+226%), gaining +4.9 net instructions per commit, and the older an instruction is, the less likely it is to be deleted (log-hazard -0.032/commit). Tests a fix — prompt comments encoding an instruction's latent reasoning — by inverting IFEval into synthetic 'verifiable worlds' with known-optimal instruction sets: comments cut excess instructions from +211.3% to +1.4% (a 99.3% reduction). Applied to WildIFEval, the same comments improved real-world agentic instruction-following by up to 23.1%."
  - id: story-ffff9fe41413e4ac
    kind: story
    sid: ffff9fe41413e4ac
  - id: agent-instruction-file-growth-editorial-synthesis
    kind: editorial-inference
    title: "Single-paper caveat and relation to session context growth"
    note: "This is currently a single-author preprint (submitted 2026-08-11) with no independent replication yet; treat the exact percentages as this paper's own reported numbers, not a settled community result, while the underlying cost-asymmetry mechanism and the qualitative direction of the fix are worth acting on regardless. It is also a distinct mechanism from agent-context-lifecycle: that concept covers a live session's conversational context growing quadratically in token cost turn-by-turn, while this one covers a persistent instruction file (CLAUDE.md, AGENTS.md, a system prompt) growing across a codebase's commit history because deletions become unverifiable once the reason for a rule is lost."
covers_evidence:
  - chakrabarti-2026-catastrophic-remembering-theory
  - chakrabarti-2026-catastrophic-remembering-benchmark
  - story-ffff9fe41413e4ac
  - agent-instruction-file-growth-editorial-synthesis
---

## Builder consequence
If your CLAUDE.md, AGENTS.md, or system prompt only ever gains rules and never loses them, that's not a discipline problem you can fix by trying harder to prune — it's a structural cost asymmetry. A 1,867-repository study found these files more than tripling in size over their lifetime, and the reason isn't that engineers are lazy about cleanup: it's that once you've forgotten *why* a rule was added, proving it's safe to remove becomes a combinatorial check nobody actually does. The fix isn't "delete more"; it's changing what you write when you add a rule in the first place.

## Short answer
Appending an instruction to an agent's instruction file costs nothing — one more line. Safely deleting one costs a proof that it won't reintroduce whatever bug or regression it was added to prevent, and once the reason is forgotten, that proof requires reasoning about how the instruction interacts with every other instruction still in the file. That verification cost grows exponentially with file size, so in practice nobody pays it, and the file only grows. The one intervention shown to reverse this: write the rationale down as a comment next to the rule when you add it, not just the rule itself.

## Builder model
Don't model an instruction file as a static document you occasionally tidy. Model it as an append-only log with an invisible, growing debt: every instruction you add without recording *why* is a future deletion decision that will cost more the longer it sits there, because the number of things it might silently depend on only grows as the file grows. "Clean sweep" rewrites don't fix this — they reset the size but not the underlying asymmetry, so the same growth pattern starts again immediately. The actual fix has to change the unit economics of deletion, not the file's current size.

## Mechanism
Consider a prompt with `|D|` instructions. Appending instruction number `|D|+1` is O(1) — write it, done. But suppose instruction `i` was added months ago to fix some specific failure, and nobody wrote down what that failure was. To safely remove it now, you'd need to know whether any of the file's other instructions only work correctly *in combination with* instruction `i` — an interaction that could, in the worst case, depend on any subset of the remaining `|D|-1` instructions. Checking all of those subsets is O(2^|D|). No team does exponential verification before deleting a line from a prompt, so the rational default becomes "leave it in," and the file accumulates rules whose purpose nobody can reconstruct.

The paper measures exactly this pattern at scale: across 247,694 instruction lifetimes in 1,867 repositories, agentic instruction files grew by +226% over their lifetime on average, adding a net +4.9 instructions per commit, and the deletion hazard falls with age (log-hazard -0.032 per commit) — the older an instruction is, the less likely anyone ever removes it. That's the signature of the cost asymmetry playing out in real repositories, not a hypothesis.

The proposed fix targets the actual bottleneck: the missing rationale, not the instruction count. Writing an instruction's *latent reasoning* as an inline comment turns "why is this here" from something you'd have to reconstruct by testing into something you can just read and re-check. To test this cleanly, the paper inverts IFEval — building synthetic "verifiable worlds" where the truly optimal, minimal instruction set is known in advance, so "excess instructions" can be measured exactly rather than estimated. Rationale-bearing comments cut excess instructions from +211.3% down to +1.4% relative to the optimal set, a 99.3% reduction in bloat. Applied to WildIFEval, a real-world instruction-following benchmark, the same intervention improved agentic instruction-following by up to 23.1% — the fix isn't just about file size, it also changes whether the agent follows the instructions correctly.

## Math intuition
`O(2^|D|)` sounds abstract until you picture what "safe to delete" actually requires. If a file has `|D|` instructions and any pair (or larger group) of them could interact — instruction B only matters *because* instruction A exists — then proving instruction A is now redundant means checking its effect across every possible combination of the others still present. The number of subsets of a set of size `n` is `2^n`, so the check grows exponentially with file size. At 10 instructions that's 1,024 combinations; at 30 instructions it's over a billion. Nobody does that check by hand, and an agent can't exhaustively re-verify it either without an explicit statement of what each instruction guards against — which is precisely what a rationale comment provides: it turns an exponential search over hidden interactions into a linear read of a stated dependency.

## Evidence
- Theory: the paper names catastrophic remembering as the structural mirror of catastrophic forgetting, and grounds the growth-only behavior in the O(1)-append vs. O(2^|D|)-verified-delete asymmetry — a mechanism, not just an observation.
- Benchmark/measured: the 247,694-instruction-lifetime, 1,867-repository measurement is an empirical characterization with a disclosed method (lifetime tracking across commit history), not a survey or anecdote; the IFEval-inversion and WildIFEval results are controlled benchmark evaluations of the proposed fix, also with disclosed method.
- Caveat: this is currently a single-author preprint submitted 2026-08-11, with no independent replication yet. The qualitative mechanism (cost asymmetry, rationale-as-fix) is sound and worth acting on; treat the specific percentages (226%, 4.9, 99.3%, 23.1%) as this paper's own reported figures, not an independently confirmed community result, until replicated.

## How to apply
- **When you add a rule to CLAUDE.md, AGENTS.md, or a system prompt, write down why next to it** — the failure it prevents or the constraint it enforces — not just what to do. This is the one intervention the paper found to actually reduce bloat, not brevity or better organization.
- **Audit instructions whose stated rationale is now stale or no longer true, and delete those first.** A documented rationale turns a combinatorial guess into a single fact-check: is the reason this was added still real?
- **Track net instructions added per commit as a metric on any file agents read as instructions.** A file drifting upward by roughly the same handful of net lines every commit, with no corresponding deletions, is this paper's growth signature, not an acceptable "just one more rule."
- **Treat old, undocumented instructions as your highest-risk debt**, not your safest ones — deletion likelihood measurably falls with age, so the longer an unexplained rule survives, the less likely it ever gets reconsidered.
- **Don't rely on periodic "clean sweep" rewrites as the fix.** They reset size, not the underlying cost asymmetry — without a rationale-comment discipline, the same unbounded growth resumes on the very next commit.

## Failure modes
- Deleting an old, undocumented instruction on a hunch, causing a regression it silently prevented — which then makes the team even more reluctant to ever delete anything again.
- Assuming the fix is "write shorter instructions" rather than "write why an instruction exists" — the measured intervention is rationale-bearing comments, not terser prose.
- Treating this as specific to CLAUDE.md when the same mechanism applies to any accreting instruction surface an agent or a team reads as authoritative: system prompts, onboarding runbooks, review checklists.
- Citing the 99.3%-bloat-reduction or +23.1%-instruction-following figures as settled, replicated science instead of what they currently are — a single preprint's own benchmark results.
- Confusing this with session-level context bloat: this mechanism is about a persistent file growing across a codebase's commit history, not a live conversation's token count growing turn by turn.

## Related
See [agent memory](/topic/agent-memory) for how agents retain and lose information across steps and sessions, and [context compaction](/topic/context-compaction) for the mechanics of shrinking accumulated context without losing what matters. `agent-context-lifecycle` is the sibling Foundations concept: it covers a single session's conversational context growing quadratically in token cost, a different failure mode from a persistent instruction file's unbounded, cross-commit growth described here.
