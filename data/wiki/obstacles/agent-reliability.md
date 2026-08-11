---
slug: agent-reliability
kind: obstacle
title: "Agents give fluent, confident-looking output even when it's wrong"
area: reliability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804, e057b58674d089fa, 68e97756211ddc61, 6f5c728ce100a70f, "1825257161299360", a2351bb6d35107c3]
updated: 2026-08-11
covers_evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804, e057b58674d089fa, 68e97756211ddc61, 6f5c728ce100a70f, "1825257161299360", a2351bb6d35107c3]
---

## TL;DR
An agent can hallucinate a fact, skip a step, or misuse a tool and still
return a fluent, confident-looking answer — nothing about the output itself
signals that it's wrong. Deciding where to trust the model's own reasoning
versus routing to a deterministic tool, and getting an agent to actually
prove its work rather than just claim success, is a distinct engineering
problem from measuring that work after the fact (see
[agent evaluation](/topic/agent-evaluation)).

## State of the art
The problem is starting to get named at the infrastructure layer instead of
treated as a prompt issue. A platform-design framing splits the job into
**tools for certainty** (deterministic code you can just trust) versus
**space for the model's own discovery**, and deciding which parts of a task
get which treatment is now an explicit architecture decision rather than
something left to the model's judgment at run time.

A three-way identity/execution/intent split sharpens *why* reliability is
hard. **Agent identity** has no purpose-built primitive yet: platforms are
retrofitting service-account and workload-identity patterns onto agents —
SPIFFE-based cryptographic identities (Gemini Enterprise), dedicated service
principals plus token brokers (Microsoft Entra) — and critics note the fit is
poor, since these treat every replica of an agent as interchangeable when two
runs of the same agent can behave differently. The same identity gap is being
filled from the security side too — see
[sandboxing, scoped credentials, and guardrails](/topic/agent-sandboxing),
whose non-human-identity and OS/microVM isolation work doubles as the
execution substrate reliability needs, even though it was built to contain a
hijacked agent rather than a merely unreliable one. **Reliable execution**
borrows the standard distributed-systems playbook — checkpoint recovery,
exactly-once guarantees, kernel-level resource quotas (cgroups), per-session
microVM/gVisor isolation — because rate limits, timeouts, and
non-determinism are ordinary infra failure modes once the agent is treated
as a workload. Brex supplies a concrete production instance of this leg:
routing production onboarding-agent workflows through Temporal Cloud instead
of a bespoke retry loop took long-running completion from roughly 96% to
99.9%, with the durable-execution runtime swapped in underneath workflow
code that stays otherwise unchanged — checkpoint recovery and exactly-once
guarantees bought as infrastructure, not re-implemented per agent. **Intent** is the newest and least-solved leg: LLMs "drift by
design," abandoning the assigned task, hallucinating a result, or reporting
false completion, and fixes split into LLM-graded trajectory/goal-shift
detection versus cheaper, non-LLM encoder classifiers that score binary task
completion — an auditability and cost trade-off, not just an accuracy one.

Getting an agent to **prove** it did the work, not just claim success, is
converging on the same idea from the practitioner side: coding-agent tooling
built specifically around requiring verifiable evidence of completion rather
than trusting the agent's own "done" signal.

A concrete implementation of "tools for certainty" shows up in a production
agent platform: a server-side gate evaluates conditions *after* the model
decides to call a tool but *before* the request is sent, so a prompt-injected
model can't talk its way past the check, paired with a step that extracts
values from prior API responses via JSONPath so later steps reference a
stored field instead of the model re-typing (and possibly hallucinating) an
ID. It's a working instance of the identity/execution split above: enforcement
lives outside the model's own decision, not inside a longer, more careful
prompt.

A separate data point complicates the "just use a faster, cheaper model"
instinct with a reliability cost: coverage of Grok 4.5 puts the coding-agent
cost cut at roughly 80% versus a comparable frontier setup, at near-frontier
speed and accuracy — but with the hallucination rate roughly doubling as
accuracy rose, the same cost/reliability trade this wiki's cost page tracks,
here left unmitigated rather than countered with a boundary contract or
harness retune.

A newer entrant works upstream of both identity and verification: a
persistent reasoning layer that watches an agent's session live and injects
a nudge the moment a past decision (a prior rejected approach, a settled
architecture choice) becomes relevant again — shifting reliability work from
"check the output after the fact" to "steer the decision before it's made."

A separate strand complicates the usual assumption that hallucination is
strictly a failure to correct: research on vision-language models finds
hallucinated captions can *improve* accuracy on some vision-language tasks by
broadening semantic coverage, even as they add noise elsewhere — a reminder
that "does the agent hallucinate" is the wrong single-axis question; what
matters is whether a given hallucination happens to widen useful context or
actively mislead the next reasoning step.

A concrete incident puts a dollar figure on the identity/execution gap above:
a three-person agency took a $14,000 AWS bill in a single day after attackers
extracted static access keys with unrestricted Bedrock access and burned them
invoking Claude models, and a separate case had an autonomous agent given
open-ended AWS access repeatedly reapply a CloudFormation template until it
was running far more infrastructure than the task needed. Both were caught by
a credit-card charge, not by AWS's own monitoring — billing tools like Cost
Explorer and Budgets work off data that lags roughly 24 hours, so they detect
overspend after the money is gone rather than stopping it. The fix is the same
scoped-credential, action-time-alerting discipline
[sandboxing](/topic/agent-sandboxing) already argues for, applied to spend
instead of data: IAM roles instead of static keys, service-control policies
blocking expensive instance families in agent-operated accounts, and
CloudTrail alerts on the API calls that spend money (`RunInstances`,
`InvokeModel`) rather than a budget alert that fires after the invoice.

A research architecture directly answers the "tools for certainty" framing
above with a named, layered design rather than a single fix: HALO
(Hallucination-Aware Layered Oversight) treats hallucination as a
*containable* failure mode rather than a property a bigger model will
eventually eliminate, and stacks six defenses — grounded generation over
approved content, constrained deterministic execution that bounds where the
model can err, multi-signal verification (an LLM judge plus evidence checks
against source text), calibrated abstention so the system declines rather
than guesses when grounding is thin, full traceability of every retrieval
and tool call, and continuous oversight that detects drift and regenerates
on threshold breaches. It's the identity/execution/intent split this page
already argues for, expressed as one composable architecture instead of
three separately-sourced controls.

## What's new
Brex's production onboarding agent supplies a concrete number for the
"reliable execution" leg this page already argues for: routing the workflow
through Temporal Cloud instead of a bespoke retry loop, with the same
workflow code otherwise unchanged, took long-running completion from
roughly 96% to 99.9% — durable execution bought as infrastructure rather
than built per agent.

Prior update: A research architecture (HALO) reframes the standing "wait for a model that
doesn't hallucinate" hope as the wrong target: it treats hallucination as a
containable failure mode and stacks six defenses — grounded generation,
constrained execution, multi-signal verification, calibrated abstention,
full traceability, and continuous drift oversight — into one composable
system rather than leaving reliability to whichever single control a team
happens to bolt on.

A concrete incident ties a dollar figure to the identity/execution gap this
page tracks: a three-person agency ate a $14,000 one-day AWS bill after
attackers extracted static access keys with unrestricted Bedrock access, and
a separate case had an autonomous agent repeatedly over-provision
infrastructure under open-ended AWS access. Neither was caught by AWS's own
billing tools — both lag roughly 24 hours behind actual spend — surfacing an
action-time-detection gap that billing guardrails built for human-speed
mistakes don't close for a machine-speed one.

## Why it matters for platform engineers
Reliability spans three layers platform teams have to build separately: an
identity system that can scope and audit what an agent does, an execution
substrate that survives crashes and rate limits without silently dropping
work, and an intent check that catches an agent quietly giving up or
declaring victory early. None of the three is solved by picking a better
model — they're infrastructure decisions, and skipping any one of them means
a confident-looking agent can be wrong, mid-task, or done without you
knowing which.
