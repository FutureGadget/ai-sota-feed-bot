---
slug: agent-error-history
title: "Should you clean an agent's mistakes out of its history?"
question: "Should you clean an agent's mistakes out of its history?"
summary: "No, not while the mistake's effect is still in the world. Controlled 2026 studies show a history edited to look clean can lower recovery below no edit at all, and that a retained failed call recovers better than a removed one."
status: active
cluster: tool-use
updated: 2026-11-13
audience: "strong-software-engineer"
related_topics: [tool-use, agent-reliability, context-compaction]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: history-vs-world-2026-cleaning-hurts
    kind: benchmark-result
    title: "Cleaning an Agent's History Hurts When the World Still Holds the Error"
    url: "http://arxiv.org/abs/2611.14654"
    sid: "567d8273d9c1fb0d"
    added: 2026-11-13
    note: "Freezes an agent mid-task with its exact world state, edits history or world, and lets a receiver model continue. On AgentCE-Bench, a truthful note beside the preserved error raises recovery from 51% to 66%; rewriting the step as a completed correct action lowers it from 50% to 44%. On AppWorld, a success receipt for a write whose effect is absent cuts task success from 45% to 28%, and raises it from 38% to 49% once the effect is present."
  - id: error-delivery-2026-same-error-different-recovery
    kind: benchmark-result
    title: "Same Error, Different Recovery: How Delivery Changes LLM Agent Behavior"
    url: "http://arxiv.org/abs/2611.11581"
    sid: "41573f419013b0c4"
    added: 2026-11-13
    note: "Holds error text fixed and varies placement, guidance, retained history, and turn structure across 13 open models (3B-70B), with pre-registered plans. A new user turn that retains the failed exchange avoids a severe stopping failure seen in Llama models when the exchange is removed. On ToolMaze it raises success on explicit errors by 14.2 points (7-8B) and 10.5 points (32-70B). No measurable gain on 24 tasks with silent corruption. A client given the exact fault kind does better still."
  - id: trajectory-study-2026-where-errors-enter
    kind: benchmark-result
    title: "Dependable Long-Horizon LLM Agents: A Trajectory-Centered Empirical Study of Where Errors Enter and Which Controls Reach Them"
    url: "http://arxiv.org/abs/2611.13254"
    sid: "94045c979b35ebe7"
    added: 2026-11-13
    note: "Full-trajectory annotation of 95 failed runs from six multi-agent systems (Who&When and MAD corpora). Faults enter early, at a median 0.18 of the run. In 72% of failed runs the trajectory already held evidence against the error; in 88% of those no agent acted on it. Something flagged a deviation in 31% of runs, but no response removed the deviated state. Restoring the agent's own state would have sufficed in 35 of 95 runs."
  - id: agent-error-history-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-11-13
    note: "The three studies measure different things: history edits against a frozen world, error delivery to open models, and post-hoc annotation of multi-agent failures. Read together they support one harness rule: the transcript is a claim about the world, so any step that rewrites it (repair, compaction, handoff) must either fix the world first or keep the error visible. The first two are single-paper results on specific benchmarks and receivers, not replicated."
---

## Builder consequence
When an agent makes a wrong tool call, the tempting fix is to tidy the transcript: drop the failed exchange, or rewrite the step as if it had gone right. Do neither until the world matches. The agent's next action depends on what the history *claims* happened, and a claim of success over an unrepaired side effect makes the agent stop checking.

## Short answer
Keep the error visible and say what is true about it. In a 2026 frozen-state study, a truthful note placed beside the preserved mistake raised recovery from 51% to 66%. Rewriting the same step as a correct completed action lowered recovery from 50% to 44%, below leaving the history alone. A second study found that removing a failed call before retrying triggers premature stopping in some models. A clean history helps only after the world is clean too.

## Builder model
An agent's history and its environment are two records of the same events, and they can disagree.

- **History** is what the transcript says happened: calls, receipts, notes.
- **World** is what actually persisted: rows written, files changed, messages sent.

Every history edit is an assertion about the world:

- **Annotate** ("step 4 wrote the wrong value; it is still there") keeps the two in agreement.
- **Rewrite** (replace the bad step with the right one) asserts the fix happened.
- **Delete** (drop the failed exchange) asserts nothing happened.

Rewrite and delete are safe only when the assertion is true. Compaction, repair loops, and subagent handoffs all make these edits, usually without checking.

## Mechanism
**The receipt outranks the evidence.** The model continues from the transcript as a trusted account of its own past. A step recorded as done is one it has no reason to re-verify. In the AppWorld arm of the frozen-state study, a success receipt for a database write whose effect was absent cut whole-task success from 45% to 28%. The same receipt raised success from 38% to 49% once the effect was present. Identical text, opposite outcome, decided by the world.

**Correct content is not enough.** Both AgentCE-Bench edits added the right value to the history. The note framed it as an open correction and helped. The completed action framed it as finished work and hurt. What matters is the claim the edit makes, not whether the right answer appears.

**Removal reads as "nothing to do."** The delivery study held error text fixed and varied where it landed. A new user turn that kept the failed exchange avoided a severe stopping failure seen in Llama models when the exchange was removed. As a recovery layer it added 14.2 points on ToolMaze explicit errors for 7-8B models and 10.5 for 32-70B. It was not the best form for every model.

**Agents rarely act on contradicting evidence unprompted.** A full read of 95 failed multi-agent runs found evidence against the error already in the trajectory in 72% of them, unused in 88% of those. That is why an explicit note outperforms leaving the model to notice.

## How to apply
- **Reconcile before you rewrite.** A repair step fixes the world first (undo the write, re-run the call), verifies with a read, and only then records success.
- **Annotate instead of deleting.** Keep the failed call and add a truthful note: what was attempted, what the world holds now, what remains open.
- **Generate receipts from observed state.** Record a write as succeeded after a read-back confirms the effect, not when the call returned.
- **Carry open errors through compaction and handoff.** Treat "unrepaired side effects" as load-bearing context alongside pinned constraints; a summary that says "updated the record" must be true.
- **Deliver errors as a new turn that retains the failed exchange**, then test that choice per model. Pass a typed fault kind when the harness knows it.
- **Re-check beliefs against the environment at checkpoints.** Faults entered at a median 18% of the run in the trajectory study.
- **Test it.** Freeze a mid-task state with a known wrong write, apply your compactor or repair step, and measure whether a fresh model fixes the remaining targets.

## Failure modes
- Rewriting a failed step as successful to "unconfuse" the model while the bad write persists.
- Dropping failed tool calls to save tokens, so the model sees no reason to retry.
- Handoff summaries that report intent ("set the price to 40") as outcome.
- Trusting a tool's return value as proof of effect.
- Assuming one error-delivery format works across models.
- Expecting delivery fixes to catch silent corruption; the delivery study measured no gain there.

## Related
See [does compacting an agent's context put its safety rules at risk?](/foundations/context-compaction-safety) for summaries that drop or invent rules, [tool use](/topic/tool-use) for calling reliability, and [agent reliability](/topic/agent-reliability).
