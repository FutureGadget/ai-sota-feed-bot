---
slug: agent-reliability
kind: obstacle
title: "Agents give fluent, confident-looking output even when it's wrong"
area: reliability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804]
updated: 2026-07-11
covers_evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804]
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
as a workload. **Intent** is the newest and least-solved leg: LLMs "drift by
design," abandoning the assigned task, hallucinating a result, or reporting
false completion, and fixes split into LLM-graded trajectory/goal-shift
detection versus cheaper, non-LLM encoder classifiers that score binary task
completion — an auditability and cost trade-off, not just an accuracy one.

Getting an agent to **prove** it did the work, not just claim success, is
converging on the same idea from the practitioner side: coding-agent tooling
built specifically around requiring verifiable evidence of completion rather
than trusting the agent's own "done" signal.

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

## What's new
The identity leg gets a concrete critique: SPIFFE-based (Gemini Enterprise)
and service-principal-based (Microsoft Entra) agent identity both retrofit
workload-identity patterns built for stateless, interchangeable replicas
onto agents whose behavior is non-deterministic per run — a mismatch the
field hasn't resolved. A new proactive-steering pattern also surfaced:
rather than only checking an agent's output after it acts, tooling can watch
a session live and inject a rule-based nudge the instant a relevant past
decision applies, intervening before the mistake instead of grading it
afterward.

## Why it matters for platform engineers
Reliability spans three layers platform teams have to build separately: an
identity system that can scope and audit what an agent does, an execution
substrate that survives crashes and rate limits without silently dropping
work, and an intent check that catches an agent quietly giving up or
declaring victory early. None of the three is solved by picking a better
model — they're infrastructure decisions, and skipping any one of them means
a confident-looking agent can be wrong, mid-task, or done without you
knowing which.
