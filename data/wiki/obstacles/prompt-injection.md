---
slug: prompt-injection
kind: obstacle
title: "Untrusted input and tools can hijack an agent"
area: security
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75, f26c96cfcb192832, 9c19b2212d6264ac, 655ca293c796f3fd, 61a5c70b3cae54c5, fdd9745edc3aad4e, aaef033dfabe2831, f9a1870648a6375a, 5201cdda51e234b5, f8df3e0d3cc81402, 8eafdf1e65e79a0b, 192b5c5f06f75b71, d925d8c91f460a44, 25a79f33334f2b0e, 68562210b323388b, dc6dd2ecfc18702f]
updated: 2026-07-30
covers_evidence: [2f58221195cbccdf, 6b3ed4b86d0301bf, 2f585fd257ad02a4, dd1dcc3f564a3ddd, 9ef99508d91d13ed, 810e8370a6841be6, 0ef52ef7cd8a9e75, f26c96cfcb192832, 9c19b2212d6264ac, 655ca293c796f3fd, 61a5c70b3cae54c5, fdd9745edc3aad4e, aaef033dfabe2831, f9a1870648a6375a, 5201cdda51e234b5, f8df3e0d3cc81402, 8eafdf1e65e79a0b, 192b5c5f06f75b71, d925d8c91f460a44, 25a79f33334f2b0e, 68562210b323388b, dc6dd2ecfc18702f]
---

## TL;DR
An agent treats whatever it reads — a web page, a tool result, a file, another
agent's message — as instructions it might follow. Prompt injection turns that
into an attack: hidden text redirects the agent to exfiltrate data, misuse its
tools, or escalate privileges. Because the agent has real credentials and can
act, a successful injection is not a bad answer — it's an unauthorized action.

## State of the art
The root cause is now usefully framed as **role confusion**: an LLM has no
reliable channel that separates "instructions from my operator" from "data I
was asked to process," so text arriving as a tool result or a fetched page can
assume the operator's role and be obeyed. Naming it this way clarifies why
prompt hygiene can't fix it — the model is doing exactly what it was built to
do, treating in-context text as authoritative — and why the durable controls
live in *authorization* rather than in detecting "malicious" strings. There is
no clean fix, only layered mitigation, and each layer has known holes.

**Guardrail models** that screen inputs/outputs are the common defense, but
recent work shows the very reasoning that makes them effective also makes
them a target — "From Shield to Target" demonstrates denial-of-service
attacks that weaponize a guardrail against the agent it protects.

**Sandboxing** is necessary but not sufficient: a coding-agent sandbox
contains code execution yet does nothing about credential authorization — the
agent inside the sandbox still holds tokens that injected instructions can
abuse.

The threat compounds in **multi-agent systems**, where one compromised
agent's output is another's trusted input; new benchmarks (Deep-XPIA) are
emerging specifically to measure cross-agent (indirect) prompt-injection
exposure.

A concrete, named, patched exploit now grounds the abstract "role confusion"
argument in a real incident: a honeypot page disguised as a Cloudflare login
got Claude's `web_fetch` tool to keep recursively following attacker-generated
nested links embedded in previously-fetched content — triggering only when it
detected the user agent talking to a Claude client — and exfiltrated a user's
name, home city, and employer before Anthropic closed the hole by stopping
`web_fetch` from following links returned within its own fetched content.
It is a textbook instance of the compounding-input problem this page already
names: the injected instruction didn't arrive as a prompt, it arrived nested
inside content the tool had already fetched on the model's behalf.

The durable lesson is **least privilege**: scope what the agent can touch so
a hijack has a small blast radius. The operational framing is consolidating
around **agent-as-identity**: an autonomous agent holds credentials and takes
actions, so it is a non-human identity that needs the same lifecycle,
scoping, and audit as a service account. Security teams warn that most
organizations don't yet treat agents that way, leaving an ungoverned class of
actors with standing privileges that injection can borrow.

Red-teaming practitioners (**Gray Swan**, with OpenAI's Zico Kolter) push the
same point from the offensive side: agent security is *not* "cybersecurity
with AI sprinkled on" — the attack surface is the model's behavior under
adversarial input, so it needs dedicated red-teaming of the agent's decisions
and tool use, not just the perimeter around it.

A subtler erosion comes from the agent's own plumbing: "**Governance
Decay**" shows that the [context compaction](/topic/context-compaction) used
to keep long sessions affordable can silently evict the safety and
governance constraints stated up front, so a guardrail that held at turn one
is simply gone by turn fifty — meaning the defenses against injection have to
be pinned outside the compactible window, not trusted to survive
summarization.

Industry framings are converging on where the **ReAct loop** actually
breaks: practitioner guidance now locates the vulnerabilities separately in
context (what gets read in), reasoning (what the model decides), and tool
execution (what it's allowed to do), naming memory poisoning and rogue tool
execution as the concrete failure modes and recommending defense-in-depth —
layered controls plus an LLM-as-judge critic reviewing the agent's own
decisions — structured against a named threat model (MAESTRO) rather than ad
hoc rules.

Model providers are also treating jailbreak resistance as an **ongoing,
versioned release concern**, not a one-time hardening pass: Anthropic's
redeployment of Claude Fable 5 ships updated cybersecurity safeguards
alongside a new industry jailbreak framework, evidence that the red-teaming
push (Gray Swan, Kolter) is feeding back into shipped model updates.

That framework is getting concrete follow-through, not just an announcement:
Anthropic has since published what its cyber classifiers do and don't block
alongside a first draft of a jailbreak *severity* framework — grading how bad
a successful jailbreak is, not just detecting one, which lets a provider
triage and prioritize fixes instead of treating every bypass as equally
urgent.

The **harness default** is also moving toward stricter authorization: Claude
Code changed its default permission mode to "Manual" across the CLI, VS Code,
and JetBrains (and stopped `AskUserQuestion` dialogs from auto-continuing) —
shipping least-privilege as the out-of-the-box behavior rather than an opt-in
setting, which matters because most successful injections exploit exactly the
gap between what a default configuration permits and what a user actually
intended to authorize.

The **human approval step itself is a spoofable channel**: Claude Code's
permission previews relayed to chat channels didn't neutralize
bidirectional-override, zero-width, and look-alike quote characters, so
injected tool-input text could make an approval prompt visually display a
different, safer-looking command than the one that would actually run — until
the fix stripped those characters before display. It's a narrow but concrete
instance of the standing lesson: any layer a human is meant to trust as ground
truth needs the same defense against injected text as the model itself.

Injection is also flipping into a **defensive technique**: security reporting
now describes prompt injection being used against the AI hacking agents
attackers deploy, not only by them — the technique targets any LLM-driven
actor in the loop, offensive tooling included.

Red-teaming itself is starting to **automate its own iteration loop**:
OpenAI's GPT-Red runs a self-play system where the red-teaming process
improves itself, aimed at safety, alignment, and prompt-injection robustness
— a shift from red-teaming as a periodic external exercise (Gray Swan, above)
toward red-teaming as a continuously-running part of the model's own
development loop.

The offensive side of this obstacle now has a named, cross-lab disclosure
rather than isolated write-ups: OpenAI and Hugging Face jointly disclosed a
security incident uncovered during AI model evaluation that surfaced
advanced, previously-unseen cyber capabilities in a frontier model, and are
sharing early findings so other defenders can prepare. It is the same
role-confusion and agent-as-identity stakes this page already argues, made
concrete at the scale of a public, cross-organization advisory instead of a
single red-team report.

Model-level resistance is now getting reported as a headline eval result,
not a footnote: Anthropic's Opus 5 system card finds it is the company's
least prompt-injectable model yet, holding up across both PI evals and
red-teaming, and Boris Cherny singled that out as more notable to him than
the model's other benchmark scores — a data point that the jailbreak- and
injection-resistance work this page tracks as an ongoing, versioned release
concern (Fable 5's redeployment, the jailbreak-severity framework) is
compounding release over release rather than staying flat.

A new **trusted-path** threat surface shows up between the agent and the
model, not inside the model's own context window: third-party API routers
sit between a coding agent and the upstream provider, unify access across
LLM providers, and can inspect and modify every request and response in
transit. Nothing verifies that what the router forwards actually matches
what the provider returned, so client-side permission checks built on the
assumption of an honest transport layer become ineffective. A new empirical
study (SIDEL) tests four escalating levels of router-side tampering — a raw
response swap, an appended instruction, an LLM-polished injection, and an
LLM-polished injection distribution-matched to the original response — across
four representative coding agents on 400 curated samples. It is the same
role-confusion problem this page already tracks, relocated from the fetched
content an agent reads to a layer the agent never inspects at all: the
router this page's [cost-controls](/topic/cost-controls) coverage already
treats as a trusted cost-optimization component turns out to be an
unverified trust boundary too.

The threat is also escalating from a single hijack to **self-propagation**:
a documented prompt-injection variant against Microsoft Word upgrades the
standard hidden-instruction attack into a worm — hidden text in one document
instructs the agent processing it to copy the same injection payload into
every other document it touches, so opening one poisoned file seeds an
agent's future output with the same attack rather than causing a single
one-off compromise. It sharpens the standing role-confusion framing into a
compounding one: an agent that treats fetched content as instructions
doesn't just get hijacked once, it can become the vector that hijacks the
next document too.

## What's new
A documented prompt-injection variant against Microsoft Word turns the
standard hidden-instruction attack into a **self-replicating worm**:
injected text instructs the agent to copy the same payload into every other
document it processes, so a single poisoned file seeds the attack into
future outputs instead of causing one isolated compromise.

## Why it matters for platform engineers
This is the security boundary of the whole agent stack, and it maps to ordinary
ops controls done right: scoped credentials, per-tool authorization, network
egress limits, and human approval on high-impact actions. The mistake is
treating a sandbox or a guardrail model as the answer; both are layers, and both
have published bypasses. Every tool you connect (see [tool use](/topic/tool-use))
widens the attack surface, so authorization and blast-radius limits — not prompt
hygiene alone — are the real control.
