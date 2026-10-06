---
slug: model-switching-replay-gap
title: "Can you evaluate an agent's model router by replaying logged trajectories?"
question: "Can you evaluate an agent's model router by replaying logged trajectories?"
summary: "No. Forking live SWE-bench agent runs at a model swap shows 61-94% of later actions diverge from the log, leaving 3% of logged states valid, so replay evaluation mispredicted every outcome that depended on the swap."
status: active
cluster: evaluation
updated: 2026-10-06
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
    sid: "4e6b8920803e5949"
    added: 2026-09-05
    note: "COLM 2026. Forks live SWE-bench trajectories at a model swap, rebuilds the sandbox, and compares against same-model control forks (~900 rollouts). Swaps rewrite 61-94% of post-fork actions; 74-77% of early swaps diverge on the first action versus 6-35% of controls; 3% of logged states stay valid. All five outcome flips occur in swap arms, none in 359 controls. A log-stitching replay evaluator mispredicts every swap-dependent outcome (0.00-0.11 patch similarity)."
  - id: model-switching-replay-gap-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-09-05
    note: "A methodology result about evaluating model routers, not a routing-policy result. It says nothing about which routing policy to use, only that the common way teams check a policy before shipping measures something other than what production will do."
---

## Builder consequence
If you evaluate a per-step model router by swapping a cheaper model into one step of a logged trajectory and checking the rest of the log, you are scoring a run that stops existing at the swap. The Replay Gap study found **61-94% of later actions change** after a live swap, and replay scoring mispredicted every swap-dependent outcome. A router shipped on replay numbers is effectively untested.

## Short answer
No. Replay substitution assumes the rest of the trajectory would unfold the same way whichever model produced the swapped step. Forking live agent runs at the swap point and continuing them for real rejects that assumption: the agent takes a different path, only 3% of logged states remain reachable, and replay evaluators get the outcome wrong exactly when it matters.

## Builder model
A model swap is a fork, not an edit.

- **Replay treats the swap as a local patch.** Substitute one step, keep every later logged step, diff the ending. Cheap: no execution, no environment.
- **Reality branches.** From the swap on, the new model reads tool outputs and errors produced by its own actions, so every later step differs. The two runs share a prefix and nothing after it.

The fix is a branching rollout: fork the real trajectory at the swap, rebuild the sandbox, let the new model run, and compare against a same-model control fork. The control isolates how much divergence is the swap versus ordinary sampling noise.

## Mechanism
An agent trajectory is a chain of model output, environment response, and next model input. Each input depends on what the environment returned for the previous action. Swap the model at step N and step N+1's input is built from a different tool call, edit, or command. The next output diverges, which changes the next environment response, and the difference compounds every step. A replay evaluator that keeps consuming the original log is grading the swapped step against a continuation the swap invalidated.

Three features of the measured divergence matter for builders:

- **It starts immediately.** Most early swaps diverge on the very first post-fork action, far above the same-model control rate.
- **It shrinks late in a run only because fewer steps remain**, not because late swaps are safe to replay.
- **Outcome flips are rare but real.** Every solved-to-unsolved or unsolved-to-solved flip came from a swap arm, never a control, so final-state accuracy on replayed logs misses exactly the changes a deployment would produce.

## How to apply
- **Discount replay-measured router accuracy.** Treat it as unvalidated until confirmed with live rollouts.
- **Evaluate with branching rollouts.** Fork at the decision point, run the swapped-in model against a real or faithfully rebuilt environment, and grade the outcome, not a diff against the log.
- **Add a same-model control arm.** Without it, sampling noise and swap effects are indistinguishable.
- **Sample early swap points heavily** if your router switches models early, where first-action divergence is highest.
- **Keep cost and correctness as separate claims.** Fewer frontier calls is measured correctly from logs; unchanged success rate needs live evidence. See [model routing](/foundations/agent-model-routing) for the cost side.

## Failure modes
- Reporting replay-substitution accuracy as if it were a live production measurement.
- Assuming a swap affects only its own step.
- Favoring late swap points in evals because divergence looks smaller there.
- Running swap experiments without a same-model control, misattributing sampling noise to the swap or the reverse.
- Treating a router's cost savings as proof it is safe to ship.

## Related
See [model routing](/foundations/agent-model-routing) for the routing policy itself and [agent eval design](/foundations/agent-eval-design) for auditing an eval's correctness before trusting its score.
