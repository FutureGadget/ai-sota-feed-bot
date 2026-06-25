---
slug: agent-sandboxing
kind: solution
title: "Sandboxing, scoped credentials, and guardrails"
status: active
obstacles: [prompt-injection]
related_storylines: []
evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d]
updated: 2026-06-25
covers_evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d]
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
layer). The same instinct is reaching the **cloud-account** layer: Cloudflare now
lets you spin up and run a Workers project under a temporary, disposable account
with no standing login — an ephemeral, self-expiring credential boundary instead
of handing an agent your real account keys (worth noting, as Simon Willison does,
that the "for AI agents" framing is partly marketing — it is a general ephemeral
scoped-account feature, which is exactly the short-lived least-privilege
primitive agents need). Least privilege plus human approval on the few actions
that really matter is the most durable control. The execution-sandbox layer
itself is commoditizing into **open-source, drop-in primitives**: tools like the
open-source Workdir give an agent a disposable, isolated working directory out of
the box, so process isolation is becoming something you install rather than
build — which lowers the bar to running untrusted agent code in a box, even as the
credential-authorization gap above means the box alone is still not the boundary.

## What's new
The controls keep turning from principles into shipped primitives, now reaching
the base execution-sandbox layer itself: open-source, drop-in sandboxes
(Workdir) hand an agent a disposable isolated working directory out of the box,
commoditizing process isolation the way per-parameter permission rules (Claude
Code's `Tool(param:value)`), approval-gated writes (datasette-agent),
identity-based sandboxes that keep infra secrets out of the agent's reach
(Cordium), and ephemeral cloud accounts (Cloudflare) already did for the
authorization layers above them — all converging, alongside OS-enforced
containers and agent-as-identity, on scoped, centrally governed, short-lived,
revocable permissions rather than guardrails or process sandboxes alone.

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
