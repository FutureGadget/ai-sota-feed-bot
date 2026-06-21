---
slug: agent-sandboxing
kind: solution
title: "Sandboxing, scoped credentials, and guardrails"
status: active
obstacles: [prompt-injection]
related_storylines: []
evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563]
updated: 2026-06-21
covers_evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563]
---

## TL;DR
Assume the agent will be hijacked and limit the damage: run its code in a
sandbox, give it narrowly scoped and short-lived credentials, gate high-impact
actions behind approvals, and screen inputs/outputs with guardrails. None of
these stops injection on its own — together they shrink the blast radius of one
that gets through.

## State of the art
The layers are real but each has a published gap. **Execution sandboxes** contain
arbitrary code, but recent analysis is blunt that they "don't solve credential
authorization" — the agent inside the box still holds tokens that injected
instructions can spend, so isolating the process is not the same as isolating its
privileges. **Guardrail models** screen prompts and outputs, yet "From Shield to
Target" shows the guardrail's own reasoning can be turned into a denial-of-service
vector against the protected agent. The center of gravity is therefore moving to
**authorization**: scope what each tool/connector can do and provision it
centrally — e.g. identity-provider-managed MCP connector auth — so permissions
are explicit and revocable rather than ambient. Two reinforcing moves are
pushing this further: treating each agent as a **non-human identity** with its
own scoped credentials, lifecycle, and audit trail (rather than a sidecar on a
human's session), and pushing isolation **down into the OS** — Microsoft positions
Windows as a trust base for agents with a dedicated Execution Container so the
sandbox is an OS-enforced boundary, not just a process wrapper. These controls
are now showing up as concrete, shipping primitives rather than principles:
identity-based sandbox platforms hide infrastructure secrets from both developers
and the agent (Cordium, a self-hosted Kubernetes sandbox where the credentials
never enter the agent's reach); harness permission rules are getting fine-grained
enough to match a tool *call's parameters* — Claude Code's `Tool(param:value)`
syntax can, for example, block Opus subagents — so authorization is scoped per
action, not per tool; and write paths are being gated behind explicit user
approval that respects the caller's own permissions (datasette-agent's
approval-prompted `execute_write_sql`, on top of a general resource-sharing ACL
layer). Least privilege plus human approval on the few actions that really matter
is the most durable control.

## What's new
The controls are turning from principles into shipped primitives: per-parameter
permission rules (Claude Code's `Tool(param:value)`, e.g. blocking Opus
subagents), approval-gated writes that honor the caller's permissions
(datasette-agent), and identity-based sandboxes that keep infra secrets out of
the agent's reach entirely (Cordium) — converging, alongside OS-enforced
containers and agent-as-identity, on scoped, centrally governed, revocable
permissions rather than guardrails or process sandboxes alone.

## Trade-offs
More isolation and tighter scopes mean more friction: approval gates add latency
and human cost, narrow credentials break workflows that legitimately need broad
access, and sandboxes add ops overhead. Guardrail models add a per-call cost and
a new failure/attack surface of their own. The honest stance is defense in depth
with no single layer trusted — which is more moving parts to build and monitor.
Best calibrated to blast radius: heavy controls on agents with write access or
money/data reach, lighter on read-only ones.

## Why it matters for platform engineers
This is standard security engineering applied to a new actor: least privilege,
short-lived scoped tokens, egress limits, and approvals — not prompt cleverness.
The actionable lesson is to treat the sandbox as containing *code* and the
credential/authorization layer as containing *capability*, and to govern tool
access centrally (see [MCP](/topic/mcp)) so a hijacked agent can reach little.
