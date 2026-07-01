---
slug: prompt-injection
kind: obstacle
title: "Untrusted input and tools can hijack an agent"
area: security
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75, f26c96cfcb192832, 9c19b2212d6264ac, 655ca293c796f3fd, 61a5c70b3cae54c5, fdd9745edc3aad4e]
updated: 2026-07-01
covers_evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75, f26c96cfcb192832, 9c19b2212d6264ac, 655ca293c796f3fd, 61a5c70b3cae54c5, fdd9745edc3aad4e]
---

## TL;DR
An agent treats whatever it reads — a web page, a tool result, a file, another
agent's message — as instructions it might follow. Prompt injection turns that
into an attack: hidden text redirects the agent to exfiltrate data, misuse its
tools, or escalate privileges. Because the agent has real credentials and can
act, a successful injection is not a bad answer — it's an unauthorized action.

## State of the art
The root cause is now usefully framed as **role confusion**: an LLM has no
reliable channel that separates "instructions from my operator" from "data I was
asked to process," so text arriving as a tool result or a fetched page can assume
the operator's role and be obeyed. Naming it this way clarifies why prompt hygiene
can't fix it — the model is doing exactly what it was built to do, treating
in-context text as authoritative — and why the durable controls live in
*authorization* rather than in detecting "malicious" strings. There is no clean
fix, only layered mitigation, and each layer has known holes.
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
not just the perimeter around it. A subtler erosion comes from the agent's own
plumbing: "Governance Decay" shows that the [context compaction](/topic/context-compaction)
used to keep long sessions affordable can silently evict the safety and
governance constraints stated up front, so a guardrail that held at turn one is
simply gone by turn fifty — meaning the defenses against injection have to be
pinned outside the compactible window, not trusted to survive summarization.
Industry framings are converging on where the ReAct loop actually breaks:
practitioner guidance now locates the vulnerabilities separately in **context**
(what gets read in), **reasoning** (what the model decides), and **tool
execution** (what it's allowed to do), naming memory poisoning and rogue tool
execution as the concrete failure modes and recommending defense-in-depth —
layered controls plus an LLM-as-judge critic reviewing the agent's own decisions
— structured against a named threat model (MAESTRO) rather than ad hoc rules.
Model providers are also treating jailbreak resistance as an ongoing, versioned
release concern, not a one-time hardening pass: Anthropic's redeployment of
Claude Fable 5 ships updated cybersecurity safeguards alongside a new
industry jailbreak framework, evidence that the red-teaming
push (Gray Swan, Kolter) is feeding back into shipped model updates.

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
Two framings sharpened this week: injection is fundamentally **role confusion**
(the model can't separate operator instructions from in-context data), and the
agent's own context-management layer is part of the attack surface — Governance
Decay shows compaction can erase the safety constraints that were supposed to hold.
The defensive primitives keep moving down the stack: the **network egress
perimeter** is now landing as a managed control, with Google Cloud's VPC Service
Controls extending its data-exfiltration boundary to agents so a hijacked agent
holding valid credentials still cannot move protected data out — limiting *where
data can go*, not just what the agent is authorized to do (see
[sandboxing](/topic/agent-sandboxing)). Practitioner guidance is now naming the
**ReAct loop's three attack points** explicitly — context, reasoning, tool
execution — and pairing memory-poisoning and rogue-tool-execution risks with a
named threat model (MAESTRO) and an LLM-judge critic reviewing agent decisions,
while providers ship jailbreak-hardening as a **release-cycle concern**
(Anthropic's Fable 5 redeploy bundling a new industry jailbreak framework), not a
one-time model property.

## Why it matters for platform engineers
This is the security boundary of the whole agent stack, and it maps to ordinary
ops controls done right: scoped credentials, per-tool authorization, network
egress limits, and human approval on high-impact actions. The mistake is
treating a sandbox or a guardrail model as the answer; both are layers, and both
have published bypasses. Every tool you connect (see [tool use](/topic/tool-use))
widens the attack surface, so authorization and blast-radius limits — not prompt
hygiene alone — are the real control.
