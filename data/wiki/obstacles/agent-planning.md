---
slug: agent-planning
kind: obstacle
title: "Agents plan multi-step work badly — they loop, stall, or skip steps"
area: planning
status: active
solutions: [agent-orchestration]
obstacles: []
related_storylines: []
evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda]
updated: 2026-07-01
covers_evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda]
---

## TL;DR
Give an agent a goal that takes ten steps and it will often take the wrong ones:
charge ahead on an ambiguous request instead of asking, decompose the task into a
plan that drifts, get stuck in a retry loop, or skip a step it needed. Planning —
turning a goal into the right ordered sequence of actions, and knowing when to stop
or ask — is a distinct failure mode from tool use or memory, and it's where
long-horizon agents most visibly fall down.

## State of the art
The dominant control structure is still the **ReAct loop** (reason → act → observe,
repeat), and the production lesson is that the loop alone isn't enough — Stripe's
financial-compliance agent pairs a ReAct framework with dedicated infrastructure
and guardrails to keep multi-step runs on track at production scale, evidence that
planning reliability is an architecture problem, not a prompt. Two refinements are
emerging on top. First, **knowing when to ask vs. proceed**: DiscoBench measures
clarification-aware deep search, scoring whether an agent recognizes an
under-specified goal and asks rather than confidently planning down the wrong path —
treating "ask a question" as a first-class planning action. Second, **learning to
plan from experience** rather than re-deriving a plan cold each run: GUI agents that
autonomously explore and reuse *hindsight* experience plan repetitive interface
tasks better than zero-shot decomposition, and DAIN's dynamic agent-interaction
network adapts the collaboration/reasoning structure to the task instead of running
a fixed plan. The through-line is that robust planning comes from *structure around
the loop* — explicit decomposition, clarification gates, learned priors, and a
harness that can re-plan — not from a single cleverer prompt. That the loop
itself is now the industry's shared vocabulary for this problem showed up at the
AI Engineer World's Fair, where "loops" and "software factories" — production
setups that wrap a planning loop in enough infrastructure to run it repeatedly and
reliably — were a dominant theme alongside forward-deployed engineering, evidence
that planning-as-harness-problem has moved from research framing to mainstream
practitioner conversation.

## Why it matters for platform engineers
Bad planning is what turns a capable model into an unreliable agent: it's the source
of runaway loops (a [cost](/topic/agent-cost) problem), of confidently wrong work on
ambiguous tickets, and of the long-horizon failures that erode trust. The
engineering job is to wrap the model's reasoning in a controllable harness —
bounded loops, explicit decomposition, clarification checkpoints, and re-planning on
failure — and to prove it works with [trajectory-level eval](/topic/agent-evaluation)
rather than hoping a bigger model plans better on its own. Planning sits upstream of
[orchestration](/topic/agent-orchestration): once you can decompose reliably, the
question becomes who executes each step.
