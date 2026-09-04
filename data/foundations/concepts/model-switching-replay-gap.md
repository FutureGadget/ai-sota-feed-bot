---
slug: model-switching-replay-gap
title: "Can you evaluate an agent's model router by replaying logged trajectories?"
question: "Can you evaluate an agent's model router by replaying logged trajectories?"
summary: "No — a controlled branching-rollout study forked live SWE-bench agent trajectories at a model swap and found 61-94% of the actions after the swap diverge from what was logged, leaving only 3% of replayed states valid, so a static replay evaluator mispredicted every outcome that actually depended on the swap."
status: active
cluster: evaluation
updated: 2026-09-04
audience: "strong-software-engineer"
math_depth: ""
related_topics: [agent-evaluation, agent-benchmarks, agent-cost]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: gonuguntla-2026-replay-gap
    kind: benchmark-result
    title: "The Replay Gap: Static Evaluation of Model Switching in LLM Agents Scores the Wrong World"
    url: "https://arxiv.org/abs/2608.08239"
    note: "Ashritha Gonuguntla, accepted at COLM 2026. Tests the standard practice of evaluating a per-step agent model router by replaying a logged trajectory and substituting another model's recorded output, which assumes the rest of the trajectory is unaffected. The study forks live SWE-bench agent trajectories at controlled points, rebuilds the sandbox environment, continues each fork with a different model, and compares against same-model control forks that isolate ordinary sampling and replay noise. Across six paired runs (~900 rollouts), model-swap forks exceed their matched same-model control floors by +0.25 to +0.66 normalized edit distance (multiplicity-corrected confidence intervals exclude zero), rewriting 61-94% of the actions taken after the fork point. 74-77% of early swaps diverge at the very first post-fork action, versus 6-35% of same-model controls, leaving only 3% of the originally logged post-fork states still valid to replay against. Divergence decreases the deeper into the trajectory the fork happens, in both swap and control arms. All five task-outcome flips observed in the study occur in swap arms (upgrades rescuing an otherwise-unsolved instance, one downgrade losing the sole solve) and zero occur across 359 control forks. When the same swaps are scored with a log-stitching replay evaluator instead of a live rollout, the replay evaluator mispredicts every outcome call that actually depended on the swap and predicts patches with only 0.00-0.11 similarity to what the live rollout actually produced."
  - id: story-4e6b8920803e5949-replay-gap
    kind: story
    sid: "4e6b8920803e5949"
  - id: model-switching-replay-gap-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "This is a methodology result about evaluating agentic model routers, not a routing-strategy result — it says nothing about which routing policy to use (see the model-routing concept for that), only that the common way teams check whether a routing policy is safe to ship is measuring something other than what will actually happen in production."
covers_evidence:
  - gonuguntla-2026-replay-gap
  - story-4e6b8920803e5949-replay-gap
  - model-switching-replay-gap-editorial-synthesis
---

## Builder consequence
If you evaluate a per-step model router — swap a cheaper model in for one step of a logged agent trajectory and check whether the rest of the recorded trajectory still looks right — you are measuring a world that stops existing the moment you make the swap. A controlled study that actually forked live SWE-bench trajectories at the swap point found 61-94% of the agent's later actions changed once a different model took over, and a standard replay evaluator scored every swap-dependent outcome wrong as a result. If you shipped a router using replay numbers, you don't actually know whether it works.

## Short answer
No. Replaying a logged trajectory and substituting one model's output for another's assumes the rest of the trajectory would have happened the same way regardless of which model produced that step — an assumption the underlying paper tests directly and rejects. Forking live agent runs at the swap point and continuing them for real, instead of replaying the original log, shows the agent takes a substantially different path after a model swap: 61-94% of post-fork actions differ from what was logged, and static replay evaluators built on the old log mispredict the resulting outcome almost every time it actually mattered.

## Builder model
Two different things can happen after you swap a model mid-trajectory, and only one of them is what replay evaluation checks for:

- **Replay evaluation assumes a swap is a local edit.** Substitute the new model's output for one step, keep every later step exactly as logged, and diff the ending. This is cheap — no agent execution, no environment, just string comparison against an existing log.
- **A model swap is actually a fork, not an edit.** Once a different model produces step N, the environment state, the model's own next input, and every subsequent decision differ from the logged run — because the new model reads the tool outputs and errors that its own actions produced, not the ones the original model's actions produced. The two trajectories are genuinely different runs from that point forward, not one run with a single step patched.

The paper's branching-rollout method makes this fork explicit instead of assuming it away: fork the real trajectory at the swap point, rebuild the actual sandbox, and let the new model run for real. Comparing that against a same-model control fork (same swap mechanics, same model on both sides) isolates how much of the divergence is the model swap itself versus ordinary sampling noise any two runs would show.

## Mechanism
An agentic trajectory is a sequence of (model output → environment response → next model input) steps, and each step's input depends on everything the environment returned from the step before it. Swap the model at step N, and step N+1's input is now built from a different model's tool call, file edit, or command — not the one the log recorded. The next model reasons over a different context than the original run ever produced, so its own output diverges, which changes the environment response again, compounding at every subsequent step. A replay evaluator that keeps consuming the original log's later steps is checking the new model's swapped-in step against a continuation the swap itself invalidated.

The study's numbers show how fast this compounds: 74-77% of early swaps diverge at the very first action after the fork (versus 6-35% for same-model controls, which isolates how much of that is just normal run-to-run variance rather than the swap), and by the time the trajectory reaches its end only 3% of the originally logged states are still states the forked run actually passes through. Divergence shrinks the closer the swap happens to the end of the trajectory simply because there are fewer remaining steps left to diverge in — not because late swaps are safer to replay-evaluate.

The outcome-level consequence is asymmetric and rare but real: all five task-outcome flips (an unsolved instance becoming solved, or the reverse) happened in swap forks, never in same-model controls, meaning a router evaluated only by looking at final-state accuracy on replayed logs can miss exactly the outcome changes a real deployment would produce.

## Evidence
Benchmark-result-backed: a controlled empirical study (COLM 2026) using branching rollouts on live SWE-bench agent trajectories, with a same-model control arm specifically designed to separate the model-swap effect from ordinary sampling and replay noise, and multiplicity-corrected confidence intervals on the reported divergence gap. The 3% valid-state figure, the 61-94% action-rewrite range, and the 0.00-0.11 patch-similarity result under a log-stitching replay evaluator are all measured outcomes of that experiment, not modeled estimates. Editorial synthesis: framing this as a caution specifically for agentic model-routing evaluation, distinct from the routing-policy question itself, is LLM Digest's own read of what the result implies for builders.

## How to apply
- **Don't trust a per-step router's reported accuracy if it was measured by replaying logged trajectories.** The replay evaluator in this study mispredicted every outcome call that depended on the swap — a router that looks safe on replay numbers has not actually been tested against what happens when it runs.
- **Evaluate a router with live rollouts from the swap point forward, not log substitution.** Fork the trajectory at the decision point, let the swapped-in model actually execute against a real (or realistically rebuilt) environment, and grade the resulting outcome — not a diff against the original log's later steps.
- **Add a same-model control arm to your own routing evals.** Comparing swap forks only against the original log conflates the swap's effect with ordinary run-to-run variance; a same-model control fork (identical mechanics, no swap) tells you how much divergence exists even when nothing changed.
- **Expect divergence to be worst for swaps early in a trajectory and weight your eval sampling accordingly.** If your router mostly swaps models early (before much context has accumulated), that's exactly where this study found the highest first-action divergence rate (74-77%).
- **Treat a router's reported cost savings and its reported accuracy as two separate claims that need two separate kinds of evidence.** The cost savings a router reports are usually measured correctly (fewer frontier calls); whether the resulting agent still succeeds at the same rate is the claim replay evaluation can't actually support — see [when should an agent route a call to a cheaper model?](/foundations/agent-model-routing) for the cost side of this design decision.

## Failure modes
- Reporting a model router's accuracy from replay-substitution experiments and treating it as equivalent to a live production measurement, when the study here shows replay mispredicts almost every outcome that actually depended on the swap.
- Assuming a model swap only affects the one step it's applied to, missing that every later step's input already depends on what the swapped-in model's own actions produced, not what the original log recorded.
- Sampling routing-eval swap points late in trajectories because divergence looks smaller there, without accounting for the fact that there's simply less trajectory left to diverge in, not that late swaps are actually safer.
- Running swap experiments without a same-model control arm, so ordinary sampling noise gets misattributed to the model swap itself (or vice versa).
- Treating a router's cost-savings numbers as proof the router is safe to ship, when cost and correctness are measured by entirely different methods and only one of them was actually validated live.

## Related
See [when should an agent route a call to a cheaper model?](/foundations/agent-model-routing) for the routing-policy side of this decision — the shape production routers use to decide when to escalate — and [what should an agent eval actually measure?](/foundations/agent-eval-design) for the broader discipline of auditing an eval's own correctness before trusting the score it reports, which this concept applies specifically to the case of a per-step model router.
