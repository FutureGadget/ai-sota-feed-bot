---
slug: prompt-injection
kind: obstacle
title: "Untrusted input and tools can hijack an agent"
area: security
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75]
updated: 2026-06-23
covers_evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75]
---

## TL;DR
An agent treats whatever it reads — a web page, a tool result, a file, another
agent's message — as instructions it might follow. Prompt injection turns that
into an attack: hidden text redirects the agent to exfiltrate data, misuse its
tools, or escalate privileges. Because the agent has real credentials and can
act, a successful injection is not a bad answer — it's an unauthorized action.

## State of the art
There is no clean fix, only layered mitigation, and each layer has known holes.
**Guardrail models** that screen inputs/outputs are the common defense, but
recent work shows the very reasoning that makes them effective also makes them a
target — "From Shield to Target" demonstrates denial-of-service attacks that
weaponize a guardrail against the agent it protects. Sandboxing is necessary but
not sufficient: a coding-agent sandbox contains code execution yet does nothing
about **credential authorization** — the agent inside the sandbox still holds
tokens that injected instructions can abuse. The threat compounds in multi-agent
systems, where one compromised agent's output is another's trusted input; new
benchmarks (Deep-XPIA) are emerging specifically to measure cross-agent
(indirect) prompt-injection exposure. The durable lesson is **least privilege**:
scope what the agent can touch so a hijack has a small blast radius — and the
operational framing is consolidating around **agent-as-identity**: an autonomous
agent holds credentials and takes actions, so it is a non-human identity that
needs the same lifecycle, scoping, and audit as a service account. Security teams
warn that most organizations don't yet treat agents that way, leaving an
ungoverned class of actors with standing privileges that injection can borrow.
Red-teaming practitioners (Gray Swan, with OpenAI's Zico Kolter) push the same
point from the offensive side: agent security is *not* "cybersecurity with AI
sprinkled on" — the attack surface is the model's behavior under adversarial
input, so it needs dedicated red-teaming of the agent's decisions and tool use,
not just the perimeter around it.

## What's new
The emphasis is moving up the stack from "filter the prompt" to "govern the
actor": guardrails can be turned into a DoS vector and sandboxes don't solve
credential authorization, while a parallel push reframes every agent as a
first-class **identity** to be provisioned, scoped, and audited like a service
account — closing the gap injection exploits when agents hold ambient privilege.
The least-privilege controls are now landing as concrete harness primitives —
per-parameter permission rules (Claude Code's `Tool(param:value)`) and
approval-gated writes that respect the caller's permissions (datasette-agent) —
so blast-radius limiting is becoming a configurable boundary, not just advice.
And on the offensive side, red-teamers (Gray Swan, Zico Kolter) are pressing that
agent security is a distinct discipline from classic cybersecurity, requiring
adversarial testing of the agent's own behavior rather than perimeter defense.

## Why it matters for platform engineers
This is the security boundary of the whole agent stack, and it maps to ordinary
ops controls done right: scoped credentials, per-tool authorization, network
egress limits, and human approval on high-impact actions. The mistake is
treating a sandbox or a guardrail model as the answer; both are layers, and both
have published bypasses. Every tool you connect (see [tool use](/topic/tool-use))
widens the attack surface, so authorization and blast-radius limits — not prompt
hygiene alone — are the real control.
