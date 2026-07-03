---
slug: agent-planning
kind: obstacle
title: "Agents plan multi-step work badly — they loop, stall, or skip steps"
area: planning
status: active
solutions: [agent-orchestration]
obstacles: []
related_storylines: []
evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda, 9776829397d5307a, 9ae3d20f85fa904c, 9bf2f6419fda7872, 2566c8933f2e65d1, 7e29fd14ca16f2a8, cf0a37dd32efaf51, 6d061c8f299a97ab]
updated: 2026-07-03
covers_evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda, 9776829397d5307a, 9ae3d20f85fa904c, 9bf2f6419fda7872, 2566c8933f2e65d1, 7e29fd14ca16f2a8, cf0a37dd32efaf51, 6d061c8f299a97ab]
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

"The loop" is now solidifying into an engineered, reusable artifact rather than
a one-off prompt pattern. A provider-agnostic reference implementation built on
ports-and-adapters (call model, run tools, feed results back, stop) treats the
loop itself as portable infrastructure any OpenAI-compatible backend can plug
into, and QUALITY.md proposes an open spec, agent skill, and CLI for grading
"loop engineering" quality directly — naming and measuring the harness-quality
axis rather than leaving it implicit. Self-improving variants are also
emerging: an "autoresearch" pattern has agents iterate on their own task
*recipes* across runs, closing a feedback loop over the plan itself rather than
just over individual steps, though practitioners are explicit that humans stay
central to steering it — the case against one-shot AI design argues skill
engineering (iterative, human-curated task specs) beats hoping a single prompt
gets the plan right.

The "know when to ask vs. proceed" thread also gains a metacognitive angle:
CoMet targets uncertainty estimation directly — decomposing *what kind* of
uncertainty a multimodal model has, since "knowing what you don't know" is
exactly the signal a planning loop needs to decide whether to ask a
clarifying question or charge ahead, extending DiscoBench's clarification-aware
benchmark with a mechanism for producing that signal in the first place.

Training is starting to target planning **directly**, not just the harness
around it: OpenAI's Agent RFT fine-tunes reasoning models against reward
signals from real tool interactions, using reinforcement learning to solve the
credit-assignment problem — which of the many steps in a long trajectory
actually caused success or failure — rather than relying entirely on prompting
or a hand-built harness to keep the loop on track.

## What's new
Training is starting to target planning directly: OpenAI's Agent RFT
fine-tunes reasoning models against tool-interaction reward signals, using RL
to solve credit assignment across a long trajectory rather than leaning only
on harness engineering. Alongside it, "the loop" is solidifying into
reusable, gradeable infrastructure — a provider-agnostic ports-and-adapters
reference loop, an open spec for grading loop-engineering quality
(QUALITY.md), and self-improving "autoresearch" loops that iterate on their
own task recipes — while practitioners push back that human steering (skill
engineering) still beats one-shot design. CoMet adds a metacognitive signal
(decomposed uncertainty estimation) to the "ask vs. proceed" question
DiscoBench already benchmarks.

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
