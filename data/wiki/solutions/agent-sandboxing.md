---
slug: agent-sandboxing
kind: solution
title: "Sandboxing, scoped credentials, and guardrails"
status: active
obstacles: [prompt-injection]
related_storylines: []
evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d, 8a98677361367a46, 655ca293c796f3fd, 4dca27f5d11655f3, 0d10a691ebcb0e61, f9a1870648a6375a, 7a882200fe85650f]
updated: 2026-07-03
covers_evidence: [2f585fd257ad02a4, 6b3ed4b86d0301bf, b2c537fce6444ae6, dd1dcc3f564a3ddd, b36dcebbf2119ee1, 4c55eebe122eae12, 9ef99508d91d13ed, 810e8370a6841be6, 68a519e26dde7563, ed140b4e4c38f7b0, ca0cc4b843525e7d, 8a98677361367a46, 655ca293c796f3fd, 4dca27f5d11655f3, 0d10a691ebcb0e61, f9a1870648a6375a, 7a882200fe85650f]
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
- **Secure defaults at the harness level**: Claude Code changed its default
  permission mode to "Manual" across the CLI, VS Code, and JetBrains, shipping
  least privilege as the out-of-the-box behavior rather than an opt-in a team
  has to discover and turn on.
- **External output verification**: SonarQube plugins now run trusted static
  analysis over code written by Claude Code, Copilot, Codex, and Cursor,
  adding an independent, non-model check on what the sandbox lets an agent
  produce — a control on the agent's *output*, complementing the controls
  above on its execution and credentials.

Least privilege plus human approval on the few actions that really matter
remains the most durable control across all of these layers.

## What's new
Two controls extend the "assume compromise" stack in different directions:
**secure-by-default harness configuration** (Claude Code's default permission
mode moving to "Manual" across its CLI and IDE integrations) closes the gap
between what a default setup permits and what a user actually intended, while
**independent output verification** (SonarQube's trusted static-analysis
plugins for Claude Code, Copilot, Codex, and Cursor) adds a non-model check on
what an agent produces rather than only on what it's allowed to do.

That builds on the network-perimeter control (Google Cloud VPC Service
Controls), operated platforms (Grab's Palana), and the commoditized base
layer of drop-in sandboxes and tool-call firewalls (Workdir, Cerberus).

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
