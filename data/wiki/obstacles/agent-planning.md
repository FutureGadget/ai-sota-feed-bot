---
slug: agent-planning
kind: obstacle
title: "Agents plan multi-step work badly — they loop, stall, or skip steps"
area: planning
status: active
solutions: [agent-orchestration]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: loop-as-infrastructure
    title: The agent loop as reusable infrastructure
    summary: The reason-act-observe loop is now packaged as frameworks, portable libraries, and production harnesses; vendors agree that structure around the loop, not a cleverer prompt, keeps multi-step runs on track.
  - key: ask-or-proceed
    title: Deciding when to ask, explore, or how much to do
    summary: Clarification benchmarks, uncertainty signals, live state models, scope estimation, and reasoning-effort dials give a harness explicit moves before it commits to a plan.
  - key: verify-and-replan
    title: Verification loops and re-planning on failure
    summary: Bounded worker/critic pairs, rubric graders with iteration caps, test-anchored coding, and multi-hypothesis failure diagnosis replace blind retry with an explicit check-then-revise step.
  - key: learned-planning
    title: Learning to plan from experience, RL, and code
    summary: Agents improve plans with hindsight experience, RL on real tool interactions, evolvable harnesses, and plans written as reusable code; the evaluation signal remains the limiting factor.
  - key: measuring-planning
    title: Benchmarks for loops and long-horizon procedures
    summary: New benchmarks score the loop controller separately from the agent, test reasoning about the harness's own lifecycle, and stretch planning horizons to hundreds of pages of procedures.
---

## TL;DR
Give an agent a goal that takes ten steps and it will often take the wrong
ones: charge ahead on an ambiguous request instead of asking, follow a plan
that drifts, get stuck in a retry loop, or skip a step it needed. Planning,
turning a goal into the right ordered actions and knowing when to stop or ask,
is a distinct failure mode from tool use or memory.

## State of the art
**Robust planning comes from structure around the loop, not a better prompt.**
The ReAct loop (reason, act, observe, repeat) is the shared base, and the
field now treats it as engineered infrastructure: framework APIs with
persisted state and detached turns, portable loop libraries, and hooks that
change an agent's tools mid-run. LangGraph, GitHub, and OpenAI describe the
same practice under different names: graph, loop, or harness engineering.

Three refinements sit on top of the loop:

- **Decide before committing.** Ask for clarification on vague goals, explore
  when the path is unclear, estimate how much work a task needs, and set
  reasoning effort per step. Scope estimation alone cut cost 85% at equal
  success in one benchmark.
- **Verify, then revise.** Bounded worker/critic pairs, rubric graders with an
  iteration cap, and tests that guide implementation replace open-ended retry.
  Diagnosing why a step failed, across several hypotheses, is itself a
  planning step.
- **Learn the plan.** Hindsight experience, RL on real tool interactions, and
  agents that write plans as reusable code all beat re-deriving a plan cold.
  Coding agents' synthesized planners outperformed hand-engineered ones.

**How the harness carries state between steps matters as much as the model.**
Retaining reasoning and enabling compaction roughly tripled one model's
ARC-AGI-3 score.

**The open problem is measurement.** Self-improving loops are only as good as
their evaluator, and an end-to-end pass/fail cannot tell whether the agent or
the loop failed. Benchmarks that score the loop controller separately and test
procedures hundreds of pages long are first steps; production teams still lean
on humans for most planning decisions.

## Why it matters for platform engineers
Bad planning turns a capable model into an unreliable agent. It causes runaway
loops (a [cost](/topic/agent-cost) problem), confidently wrong work on
ambiguous tickets, and the long-horizon failures that erode trust. The job is
to wrap the model in a controllable harness: bounded loops, explicit
decomposition, clarification checkpoints, verification, and re-planning on
failure. Prove it with [trajectory-level eval](/topic/agent-evaluation)
rather than hoping a bigger model plans better. Planning sits upstream of
[orchestration](/topic/agent-orchestration): once you can decompose reliably,
the question becomes who executes each step.
