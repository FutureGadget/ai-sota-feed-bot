---
slug: agent-sandboxing
kind: solution
title: "Sandboxing, scoped credentials, and guardrails"
status: active
obstacles: [prompt-injection]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: credential-boundary
    title: Keeping secrets and authority out of the sandbox
    summary: Sandboxes don't scope the tokens inside them, so secrets move to identity-based access, ephemeral accounts, and egress proxies that inject real credentials only on the wire.
  - key: permission-policy
    title: Scoping what the agent may do
    summary: Permissions are getting finer and more central, with per-parameter rules, approval-gated writes, IdP-managed connectors, sequence-aware policy, and portable permission specs.
  - key: local-sandboxes
    title: Local sandboxes and tool-call supervisors
    summary: OS-enforced sandboxes, install-and-go runners, and syscall or tool-call firewalls make local isolation a commodity; Claude Code reports 84% fewer permission prompts.
  - key: managed-platforms
    title: Managed and self-hosted sandbox platforms
    summary: MicroVM platforms from Modal, Docker, Azure, and Cloudflare, plus self-hosted hypervisors and paved-road internal platforms, compete on startup time, scale, and persistence.
  - key: egress-and-escapes
    title: "Real escapes: egress, allowlists, and harness bugs"
    summary: Every reported escape went through open egress, a vulnerable allowlisted host, an exposed endpoint, or a spoofable trust check, never a broken isolation primitive.
  - key: guardrails-and-verification
    title: Guardrails, red-teaming, and checks on agent output
    summary: Guardrail models can be attacked themselves, so teams add static analysis, automated remediation, continuous red-teaming, and workload inventory around the sandbox.
---

## TL;DR
Assume the agent will be hijacked and limit the damage: run its code in a
sandbox, give it narrowly scoped and short-lived credentials, gate high-impact
actions behind approvals, and screen inputs/outputs with guardrails. None of
these stops injection on its own — together they shrink the blast radius of one
that gets through.

## State of the art
**Isolation is solved well enough; the boundary around it is not.** MicroVMs,
gVisor, bubblewrap, and Seatbelt held in every reported incident. The escapes
went through open DNS/HTTPS egress, a vulnerable package proxy on the
allowlist, a customer's unauthenticated sandbox endpoint, a spoofable Host
header in a harness, or an eval prompt that falsely claimed "no internet".
Anthropic's own review found its custom proxies and allowlist code to be
the weakest link, which argues for buying the isolation primitive and
spending engineering effort on egress and authentication.

**Credentials are leaving the sandbox.** The consensus pattern is that the
agent never holds a real secret: identity-based access, ephemeral accounts,
and egress proxies that swap a placeholder for the real token only for
trusted domains, now a first-party API on Gemini Managed Agents.

**Authorization is getting finer and more central.** Per-parameter rules,
approval-gated writes, IdP-provisioned MCP connectors, policies over a
session's sequence of tool calls, and permissions packaged as OCI images
all move control from the prompt to explicit, revocable policy. Defaults
are tightening too: Manual permission mode and default-deny egress.

**Sandboxes are commoditizing at both ends.** Local install-and-go runners
and syscall supervisors cover the developer machine; managed microVM
platforms compete on subsecond starts, suspend/resume, scale to a million
concurrent sandboxes, and persistent "full computer" environments.

**The open problem is the layer that decides what is trusted.** Guardrail
models can be driven into denial of service, model-layer classifiers miss
direct injection that egress controls stop, and a false environment premise
removes containment without any attack.

## Trade-offs
More isolation and tighter scopes mean more **friction**: approval gates add
latency and human cost, narrow credentials break workflows that legitimately
need broad access, and sandboxes add ops overhead. OS-enforced sandboxes
reduce prompt fatigue but do not scope the credentials inside them.

A boundary stated in a task or prompt ("no internet access", "this is a
simulation") is not a control. The OpenAI/Hugging Face, Anthropic, and UK
AISI incidents all removed containment by configuration or false premise,
not by breaking the sandbox.

Guardrail models add per-call cost and a new failure and attack surface.
Allowlists are only as trustworthy as the hosts on them.

The honest stance is defense in depth with no single layer trusted, which
means more moving parts to build and monitor. Calibrate to **blast
radius**: heavy controls on agents with write access or money and data
reach, lighter on read-only ones.

## Why it matters for platform engineers
This is standard security engineering applied to a new actor: least privilege,
short-lived scoped tokens, egress limits, and approvals — not prompt cleverness.
The actionable lesson is to treat the sandbox as containing *code* and the
credential/authorization layer as containing *capability*, default-deny
outbound traffic, and govern tool access centrally (see [MCP](/topic/mcp)) so
a hijacked agent can reach little. Least privilege plus human approval on the
few actions that really matter remains the most durable control. See
[prompt injection](/topic/prompt-injection) for the attacks these layers contain.
