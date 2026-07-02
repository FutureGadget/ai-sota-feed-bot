---
slug: agent-sandboxing
kind: solution
title: "Sandboxing, scoped credentials, and guardrails"
status: active
obstacles: [prompt-injection]
related_storylines: []
evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d, 8a98677361367a46, 655ca293c796f3fd, 4dca27f5d11655f3, 0d10a691ebcb0e61, 7a882200fe85650f, d69dea0504b4b512, 8db233accb157cb2]
updated: 2026-07-02
covers_evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d, 8a98677361367a46, 655ca293c796f3fd, 4dca27f5d11655f3, 0d10a691ebcb0e61, 7a882200fe85650f, d69dea0504b4b512, 8db233accb157cb2]
---

## TL;DR
Assume the agent will be hijacked and limit the damage: run its code in a
sandbox, give it narrowly scoped and short-lived credentials, gate high-impact
actions behind approvals, and screen inputs/outputs with guardrails. None of
these stops injection on its own — together they shrink the blast radius of one
that gets through.

## State of the art
Each control layer has a published gap, so the field is stacking them into
defense in depth rather than trusting any one of them:

- **Execution sandboxes** contain arbitrary code, but recent analysis is blunt
  that they "don't solve credential authorization" — the agent inside the box
  still holds tokens that injected instructions can spend, so isolating the
  process is not the same as isolating its privileges.
- **Guardrail models** screen prompts and outputs, yet "From Shield to Target"
  shows the guardrail's own reasoning can be turned into a denial-of-service
  vector against the protected agent.
- **Authorization** is where the center of gravity is moving: scope what each
  tool/connector can do and provision it centrally — e.g.
  identity-provider-managed MCP connector auth — so permissions are explicit
  and revocable rather than ambient.
- **Non-human identity**: treat each agent as its own identity with scoped
  credentials, lifecycle, and audit trail, rather than a sidecar on a human's
  session.
- **OS-level isolation**: Microsoft positions Windows as a trust base for
  agents with a dedicated Execution Container, pushing the sandbox boundary
  down into the OS instead of leaving it a process wrapper.
- **Identity-based sandbox platforms** are shipping as concrete primitives:
  Cordium is a self-hosted Kubernetes sandbox where infrastructure secrets
  never enter the agent's reach.
- **Harness-level secret hiding**: Claude Code's `sandbox.credentials`
  setting blocks sandboxed commands from reading credential files and secret
  environment variables, closing part of the "the box still holds tokens" gap
  at the config layer.
- **Per-parameter permissions**: Claude Code's `Tool(param:value)` syntax can,
  for example, block Opus subagents, so authorization is scoped per action,
  not per tool.
- **Approval-gated writes**: datasette-agent's `execute_write_sql` requires
  explicit user approval on top of a general resource-sharing ACL layer,
  gating the write paths that matter.
- **Ephemeral cloud accounts**: Cloudflare now lets you run a Workers project
  under a temporary, disposable account with no standing login — a
  self-expiring credential boundary instead of handing an agent your real
  account keys (worth noting, as Simon Willison points out, that the "for AI
  agents" framing is partly marketing — it is a general ephemeral
  scoped-account feature that happens to be exactly the short-lived
  least-privilege primitive agents need).
- **Drop-in process isolation**: the open-source Workdir gives an agent a
  disposable, isolated working directory out of the box, commoditizing
  execution sandboxing into something you install rather than build — though
  the credential-authorization gap above means the box alone still isn't the
  boundary.
- **Tool-call firewalls**: Cerberus is a local firewall that sits in front of
  an agent's tool calls, mediating and blocking them at the dev machine rather
  than inside a cloud platform — the local-dev counterpart to the network
  perimeters and platform governance below.
- **Enterprise platforms**: Grab's security team built Palana, a
  Kubernetes-native secure execution platform, on the premise that
  model-driven agents — unlike deterministic software — exhibit unpredictable
  tool-use and code-writing and need a purpose-built isolation-plus-governance
  substrate to run safely in production. It packages the same controls
  (sandboxed execution, scoped access, central governance) as paved-road
  infrastructure a platform team operates.
- **Network perimeter**: Google Cloud's VPC Service Controls now adds
  agentic-AI guardrails that draw a network-level boundary around the data an
  agent can touch, so a hijacked agent holding valid tokens still cannot move
  protected data out of the perimeter — the egress-control complement to
  credential scoping (identity limits *what the agent is allowed to do*, the
  network perimeter limits *where data can go* even when an action is
  authorized).
- **Output verification**: SonarQube plugins bring trusted code verification
  to Claude Code, Copilot, Codex, Cursor, and other coding-agent tools —
  checking what the agent produced, the output-side complement to input
  screening.
- **Supply-chain guarding**: deptrust is a CLI that checks packages an agent
  is about to add against known vulnerabilities across npm, PyPI, crates.io,
  and a dozen more ecosystems, stopping a vulnerable dependency before it
  lands.
- **Offense-side containment**: dedicated guardrails for agents built for
  offensive/red-team use extend the sandboxing discipline to agents whose
  job is to attack, not just agents that might be attacked through.

Least privilege plus human approval on the few actions that really matter
remains the most durable control across all of these layers.

## What's new
Two new control surfaces round out the stack: output-side verification
(SonarQube plugins wired into Claude Code, Copilot, Codex, and Cursor)
checks what a coding agent produced rather than just what it read, and
supply-chain guarding (deptrust) blocks known-vulnerable dependencies an
agent is about to add — plus containment purpose-built for offensive/
red-team agents, not just agents that might be attacked.

The control stack is extending to the **network perimeter**: Google Cloud's VPC
Service Controls now adds agentic-AI guardrails so a hijacked agent with valid
credentials still cannot exfiltrate protected data past a network boundary — the
egress complement to credential scoping.

That joins a move to assemble controls into operated **platforms**, not just
shipped primitives: Grab built Palana, a Kubernetes-native secure execution
platform for running autonomous agents safely in production — sandboxed
execution plus scoped access and central governance as paved-road
infrastructure.

Underneath both sits a now-commoditized **base layer**: open-source drop-in
sandboxes like Workdir, and local tool-call firewalls like Cerberus that gate
an agent's actions from a single installable proxy.

The **authorization primitives** feeding all of this keep multiplying:

- per-parameter permission rules (Claude Code's `Tool(param:value)`)
- harness-level secret hiding (Claude Code's `sandbox.credentials` blocks
  sandboxed commands from reading credential files and secret env vars)
- approval-gated writes (datasette-agent)
- identity-based sandboxes that keep infra secrets out of the agent's reach
  (Cordium)
- ephemeral cloud accounts (Cloudflare)

All of it, alongside OS-enforced containers and agent-as-identity, is
converging on the same target: scoped, centrally governed, short-lived,
revocable permissions rather than guardrails or process sandboxes alone.

## Trade-offs
More isolation and tighter scopes mean more **friction**: approval gates add
latency and human cost, narrow credentials break workflows that legitimately
need broad access, and sandboxes add ops overhead. Guardrail models add a
per-call cost and a new failure/attack surface of their own.

The honest stance is defense in depth with no single layer trusted — which is
more moving parts to build and monitor. Best calibrated to **blast radius**:
heavy controls on agents with write access or money/data reach, lighter on
read-only ones.

## Why it matters for platform engineers
This is standard security engineering applied to a new actor: least privilege,
short-lived scoped tokens, egress limits, and approvals — not prompt cleverness.
The actionable lesson is to treat the sandbox as containing *code* and the
credential/authorization layer as containing *capability*, and to govern tool
access centrally (see [MCP](/topic/mcp)) so a hijacked agent can reach little.
