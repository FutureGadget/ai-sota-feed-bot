---
slug: agent-planning
kind: obstacle
title: "Agents plan multi-step work badly — they loop, stall, or skip steps"
area: planning
status: active
solutions: [agent-orchestration]
obstacles: []
related_storylines: []
evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda, 9776829397d5307a, 9ae3d20f85fa904c, 9bf2f6419fda7872, 2566c8933f2e65d1, 7e29fd14ca16f2a8, cf0a37dd32efaf51, 6d061c8f299a97ab, bfeae69131afd34f, 5a5b80258f0f8836, a98baa78edc4ea0a, 2c589c3624db6218, 0a08c765f6fbc28a, 4b81c55e5bad6a95, 8cdcaad96641fb63, 3f02e86b937e7a01, f7adfc455ef66ca9, 1e95bee9c26709cb, baa0094f7155ee33, 7a3738f365102451, 4e90420c69645ce5]
updated: 2026-07-28
covers_evidence: [1e062311eafafa88, 13b90f2d9195e871, d82e3daa1fb038a6, 28627c9767ffadd1, 49d83537b1abacda, 9776829397d5307a, 9ae3d20f85fa904c, 9bf2f6419fda7872, 2566c8933f2e65d1, 7e29fd14ca16f2a8, cf0a37dd32efaf51, 6d061c8f299a97ab, bfeae69131afd34f, 5a5b80258f0f8836, a98baa78edc4ea0a, 2c589c3624db6218, 0a08c765f6fbc28a, 4b81c55e5bad6a95, 8cdcaad96641fb63, 3f02e86b937e7a01, f7adfc455ef66ca9, 1e95bee9c26709cb, baa0094f7155ee33, 7a3738f365102451, 4e90420c69645ce5]
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
or a hand-built harness to keep the loop on track. AWS SageMaker's multi-turn
RL best practices name the same credit-assignment job from the infrastructure
side: build a training environment you can trust, run an external evaluation
separate from the reward signal, design the reward to actually match the end
task, and manage state across turns — the operational checklist underneath
"just fine-tune on tool interactions."

Re-planning on failure is also getting a more structured answer than
retry-and-hope: rather than a single reflection pass, a multi-hypothesis
failure-attribution approach has autonomous research agents generate several
candidate explanations for why an experiment failed, weigh them, and re-plan
around the most likely cause — treating failure diagnosis itself as a
planning step, not just a trigger for blind retry.

The "ask vs. proceed" question is also moving from a benchmark score to a
**live control signal**: Candidly built a per-turn state model (an IO-HMM
over signals like message length and semantic alignment) that infers whether
a conversation is Engaged, Detailed, Guided, or Disengaging and steers the
agent's next-turn behavior accordingly. Closing that loop in production
halved disengaging turns (23% → 11%) and shifted traffic toward the
high-resolution Engaged state (53% → 64%) — concrete evidence that inferring
"is this plan working" mid-episode, not just at the end, is worth the extra
model.

Lilian Weng's survey of ~35 papers on **harness engineering for recursive
self-improvement** gives the "loop as reusable infra" thread a literature
map: it names goal-oriented plan→execute→observe→improve loops, a
file-system-as-persistent-memory pattern (durable state instead of
cramming everything into context), and parent agents spawning inspectable
sub-agents as the three recurring harness design patterns, then goes one
step further than this page's existing "the loop is infra" framing —
treating the **harness code itself** as an evolvable artifact that an
LLM-driven mutation operator can improve (AlphaEvolve, Darwin Gödel
Machine), not just the prompt or the loop structure around it. The essay's
own caveat matters as much as its taxonomy: self-improvement loops work
only as well as their evaluation signal, and weak or fuzzy evaluators
remain the standing bottleneck — a reminder to pair any harness-evolution
experiment with the [trajectory-level eval](/topic/agent-evaluation) this
page already argues planning reliability depends on.

The "loop as reusable infra" thesis now has a **major-framework preview**
behind it: Google's Genkit ships an Agents API for TypeScript and Go that
packages message history, the tool-call loop, streaming, and state
persistence behind a single `chat()` interface — the same portable-loop
instinct as the provider-agnostic reference implementation above, but
shipped as a maintained framework rather than a pattern to hand-roll.
Genkit adds a primitive this page hadn't covered: **detached turns**, which
let a long-running step decouple from the request/response cycle instead of
blocking it, paired with human-in-the-loop hooks for approval gates mid-plan
— giving "ask vs. proceed" a concrete framework-level mechanism rather than
only a benchmark score (DiscoBench) or a bespoke state model (Candidly).

Planning also gains a **scope-before-you-commit** mechanism distinct from
the ask-vs-proceed and re-planning threads above: the E3 method (Estimate,
Execute, Expand) has an agent estimate a minimal operating point, execute a
minimum-sufficient path, and only expand scope once verification actually
fails. On a 121-edit benchmark it matches the strongest baseline's 100%
success rate while cutting cost 85%, tokens 91%, and files inspected 92% —
evidence that the cheapest fix for over-scoped planning is deciding how much
work a task needs *before* executing, not compressing or re-planning after
the fact.

The "loop as reusable infra" thesis gets a naming retrospective, not just
another framework: LangGraph's three-years-in review argues graph
engineering, loop engineering, and harness engineering are the same
underlying idea under three different names — putting model reasoning
inside an explicit, inspectable control structure instead of trusting a
single prompt to plan correctly — which reframes this page's own recurring
"loop as infra" thread as an industry convergence rather than one vendor's
pattern. A separate practitioner survey, "Agents in the Wild," backs that
convergence with deployment evidence: production agentic systems are moving
from research prototype to production scale specifically by adding the
structure (decomposition, checkpoints, guardrails) this page's control-
structure thread already argues for, not by relying on a stronger model
alone.

Planning also has a **reasoning-effort dial** as a distinct lever from
decomposition or clarification: providers now expose low/medium/high
reasoning-effort modes that trade latency and cost for deliberation depth on
a per-step basis, giving a harness an explicit knob for "how hard should the
model think before acting here" instead of a fixed reasoning budget applied
uniformly across every step of a plan.

**Verification loops** get a first-party, productized instance: Anthropic's
guide to Claude Code shows how to turn a developer's own manual checks (does
the output compile, does it match the spec, did the test actually pass) into
reusable skills, so the agent runs its own verification step and closes the
loop itself instead of a human re-checking every output by hand — a concrete
version of the "structure around the loop" thesis this page already argues
for, packaged as a repeatable skill rather than a one-off harness.

A concrete architecture also answers the "just scale one bigger reasoner"
default directly: PoTRE (Poly-Topological Reasoning Ensembles) decouples
inference into four heterogeneous agents — an Adversarial Refinement Agent,
a Hierarchical Strategic Planning Agent, a Spectrum Search Agent, and a
Direct Chain Agent — reconciled by a Task-Adaptive Aggregation Layer
(candidate selection, semantic synthesis, or neuro-symbolic verification)
into one global solution. On Humanity's Last Exam it reaches 49.92%
accuracy, surpassing the previous best official score, using similar or
fewer inference tokens than heavily scaled homogeneous baselines — evidence
that decomposing long-horizon planning across specialized agent roles beats
scaling one bigger single-stream reasoner, at comparable cost, the same
heterogeneous-coordination thesis [multi-agent](/topic/multi-agent) argues
for applied to planning itself.

A second major coding-agent vendor backs the "loop as reusable infra, not a
novelty to chase" convergence with its own practitioner voice: GitHub's
Copilot team frames a stable, repeatable harness — prototype, plan,
implement, review — as the thing worth building discipline around, instead
of re-architecting the workflow every time a new agent tool ships. It is
the same discipline-over-novelty argument LangGraph's three-years
retrospective makes above, this time from the other major coding-agent
product rather than a single framework vendor.

## What's new
GitHub's Copilot team frames a stable, repeatable harness — prototype, plan,
implement, review — as the durable core to build around rather than
chasing every new agent tool, echoing LangGraph's "graph/loop/harness
engineering is one idea" convergence argument from a second major
coding-agent vendor.

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
