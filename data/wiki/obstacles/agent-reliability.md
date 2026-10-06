---
slug: agent-reliability
kind: obstacle
title: "Agents give fluent, confident-looking output even when it's wrong"
area: reliability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: deterministic-boundaries
    title: Deterministic boundaries around the model
    summary: Production teams bound the model with schemas, server-side gates, type checkers, and harness invariants, so enforcement sits outside the model's own decision instead of inside a longer prompt.
  - key: execution-and-identity
    title: Agent identity, durable execution, and spend guards
    summary: Durable runtimes like Temporal deliver measured completion gains, while agent identity still borrows service-account patterns and cloud billing alerts lag agent-speed spend by about a day.
  - key: hallucination-containment
    title: Containing hallucination during and after generation
    summary: Hallucination is treated as a containable failure through layered oversight, decoding-time calibration, and calibrated detectors, with evidence that some hallucinations widen useful context rather than mislead.
  - key: verifying-the-work
    title: Proving the work instead of trusting "done"
    summary: The bottleneck has moved from generating output to verifying it; proof-of-work tooling, user-flagged errors, and verified-outcome training help, but the verifier is still the weak point for self-improving agents.
  - key: consistency-and-autonomy
    title: Consistency, autonomy limits, and the human role
    summary: Average pass rates overstate reliability, infrastructure config moves scores by up to 6 points, and humans still make most planning decisions; autonomy is a cost to justify, not a default.
---

## TL;DR
An agent can hallucinate a fact, skip a step, or misuse a tool and still
return a fluent, confident-looking answer; nothing in the output signals that
it's wrong. Deciding where to trust the model versus a deterministic tool, and
making an agent prove its work rather than claim success, is a separate
engineering problem from measuring that work afterward (see
[agent evaluation](/topic/agent-evaluation)).

## State of the art
**Reliability is a system property, not a model property.** No current model
stops hallucinating at scale, so the working answer is to contain errors with
structure around the model rather than wait for a better one.

Four patterns carry most of the weight:

- **Deterministic boundaries.** Constrained schemas, server-side gates that
  check a tool call before it is sent, compilers that reject invalid generated
  code, and harness invariants such as serialized state mutations. Enforcement
  lives outside the model's decision.
- **Durable execution.** Checkpointing and exactly-once runtimes borrowed from
  distributed systems; Brex's move to Temporal took long-run completion from
  about 96% to 99.9%. Agent identity is the weaker leg: it still borrows
  workload-identity patterns that assume every replica behaves the same.
- **Layered hallucination control.** Grounded generation, decoding-time
  calibration, calibrated detectors, and abstention, stacked as in the HALO
  architecture. Detection is precise in-domain but transfers poorly across
  domains.
- **Proof of work.** Tooling that requires evidence of completion, plus
  user-flagged error signals from production, because false completion is a
  standard failure mode.

**The measurement itself is shaky.** A ReAct agent that passes 77% of runs on
average passes all five runs only 53% of the time, and container resourcing
alone moves coding scores by up to 6 points. Humans still make about 70% of
planning decisions in Claude Code sessions, which props up reliability that
fully unattended runs would not have.

**The open problem is the verifier.** Verification is now the bottleneck, and
for agents that edit their own tools and harness, nobody has a verifier the
agent cannot also rewrite. Diagnosis has the same gap: models read logs well
but still confuse correlation with cause.

## Why it matters for platform engineers
Reliability spans three layers you build separately: an identity system that
can scope and audit what an agent does, an execution substrate that survives
crashes and rate limits without dropping work, and an intent check that
catches an agent giving up or declaring victory early. A better model fixes
none of them. Skip one and a confident agent can be wrong, stalled mid-task,
or done without you knowing which. Budget for pass-every-time evals and
action-time spend alerts, not just average accuracy and monthly billing
reports. Scoped credentials are shared with
[sandboxing](/topic/agent-sandboxing).
