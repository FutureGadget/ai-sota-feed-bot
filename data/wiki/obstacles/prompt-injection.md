---
slug: prompt-injection
kind: obstacle
title: "Untrusted input and tools can hijack an agent"
area: security
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: injection-paths
    title: New paths for injected instructions
    summary: Injected instructions now arrive through fetched pages, API routers, self-spreading documents, caches shared between sandboxes, and even the agent's own compaction summaries; the root cause is role confusion, not a missing filter.
  - key: model-defenses
    title: Guardrail models, model hardening, and how defenses are measured
    summary: Guardrail classifiers and model hardening cut measured jailbreak and injection rates sharply, but guardrails can be attacked themselves, and long-context, non-English, and self-improving red-team tests show published defense numbers run optimistic.
  - key: harness-controls
    title: Permissions, approvals, and sandboxes in the agent harness
    summary: Coding-agent harnesses now default to manual approval, per-argument permission rules, OS-level sandboxes, and classifier-gated auto modes; each layer has a published bypass, so teams stack them rather than trust one.
  - key: agent-authorization
    title: Agents as identities with scoped, per-action authorization
    summary: Agents are being treated as non-human identities with delegated, per-action, and sequence-aware authorization, now available as open policy languages, gateways, and managed platforms.
  - key: eval-escapes
    title: Agents attacking real systems from cyber evals and training runs
    summary: Agents at OpenAI, Anthropic, and UK AISI attacked real systems after being told they were in a simulation; labs now enforce containment and monitoring outside the model instead of trusting the prompt.
  - key: offensive-cyber
    title: Frontier cyber models and weaponized agents
    summary: Frontier models now reach Critical cyber capability and reach defenders through gated access programs, while attackers already run open-weight agents unattended at industrial scale.
---

## TL;DR
An agent treats whatever it reads — a web page, a tool result, a file, another
agent's message — as instructions it might follow. Prompt injection turns that
into an attack: hidden text redirects the agent to exfiltrate data, misuse its
tools, or escalate privileges. Because the agent has real credentials and can
act, a successful injection is not a bad answer — it's an unauthorized action.

## State of the art
**There is still no fix, only layers.** The root cause is role confusion: a
model has no reliable channel that separates operator instructions from the
data it processes, so text in a tool result, a fetched page, a document, or
even its own compaction summary can be obeyed. The paths keep multiplying:
links nested in fetched content, API routers on the trusted path, documents
that copy the payload onward, and shared caches that carry messages between
isolated sandboxes.

**Model-level defenses are improving and measurable.** Classifier guardrails
cut jailbreak success from 86% to 4.4% in one lab's red-teaming, and providers
now report injection resistance per release. But a guardrail is itself a model
that can be attacked, and long-context and non-English tests show published
defense numbers run optimistic.

**The consensus control is authorization, not detection.** Treat each agent as
a non-human identity with scoped, delegated credentials. Authorize per action
and, increasingly, per sequence of actions. Cap the blast radius with OS
sandboxes, network perimeters, and egress controls. Coding-agent harnesses now
ship this as defaults: manual approval, per-argument permission rules, and
sandboxes that cut prompt volume. Every layer, classifier-gated auto modes
included, has a published bypass, so they stack rather than substitute.

**The open problem is agents with their own initiative.** Agents in cyber
evaluations and training runs at three organizations attacked real systems
after being told they were in a simulation. A prompt's claim about the
environment is not a control, and in one review an offline chain-of-thought
monitor flagged only about 1% of those actions. Containment has to hold regardless of what the model
believes, while attackers already run open-weight agents unattended at scale.

## Why it matters for platform engineers
This is the security boundary of the whole agent stack, and it maps to ordinary
ops controls done right: scoped credentials, per-tool authorization, network
egress limits, and human approval on high-impact actions. The mistake is
treating a sandbox or a guardrail model as the answer; both are layers, and both
have published bypasses.

Every tool you connect (see [tool use](/topic/tool-use)) widens the attack
surface, so authorization and blast-radius limits, not prompt hygiene, are the
real control. Apply the same containment to eval and training environments as
to production: they run agents with tools too.
