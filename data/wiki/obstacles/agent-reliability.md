---
slug: agent-reliability
kind: obstacle
title: "Agents give fluent, confident-looking output even when it's wrong"
area: reliability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804, e057b58674d089fa, 68e97756211ddc61, 6f5c728ce100a70f, "1825257161299360", a2351bb6d35107c3, 8961949ff68916c0, 6a7b6e5a47f7a500, c4b4a85beb63030f, d5ceccd62fd0a295, c5e28c540d3749ce, d425cfc85457f214, 5cfa494a315266ad]
updated: 2026-08-26
covers_evidence: [ed7d246a0b0ba7d9, b29eda10951194a9, 6e5085e3c3e072bd, 1505eb481125a099, e2038a0c26803804, e057b58674d089fa, 68e97756211ddc61, 6f5c728ce100a70f, "1825257161299360", a2351bb6d35107c3, 8961949ff68916c0, 6a7b6e5a47f7a500, c4b4a85beb63030f, d5ceccd62fd0a295, c5e28c540d3749ce, d425cfc85457f214, 5cfa494a315266ad]
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
as a workload. Brex supplies a concrete production instance of this leg:
routing production onboarding-agent workflows through Temporal Cloud instead
of a bespoke retry loop took long-running completion from roughly 96% to
99.9%, with the durable-execution runtime swapped in underneath workflow
code that stays otherwise unchanged — checkpoint recovery and exactly-once
guarantees bought as infrastructure, not re-implemented per agent. **Intent** is the newest and least-solved leg: LLMs "drift by
design," abandoning the assigned task, hallucinating a result, or reporting
false completion, and fixes split into LLM-graded trajectory/goal-shift
detection versus cheaper, non-LLM encoder classifiers that score binary task
completion — an auditability and cost trade-off, not just an accuracy one.

Getting an agent to **prove** it did the work, not just claim success, is
converging on the same idea from the practitioner side: coding-agent tooling
built specifically around requiring verifiable evidence of completion rather
than trusting the agent's own "done" signal.

A concrete implementation of "tools for certainty" shows up in a production
agent platform: a server-side gate evaluates conditions *after* the model
decides to call a tool but *before* the request is sent, so a prompt-injected
model can't talk its way past the check, paired with a step that extracts
values from prior API responses via JSONPath so later steps reference a
stored field instead of the model re-typing (and possibly hallucinating) an
ID. It's a working instance of the identity/execution split above: enforcement
lives outside the model's own decision, not inside a longer, more careful
prompt.

A separate data point complicates the "just use a faster, cheaper model"
instinct with a reliability cost: coverage of Grok 4.5 puts the coding-agent
cost cut at roughly 80% versus a comparable frontier setup, at near-frontier
speed and accuracy — but with the hallucination rate roughly doubling as
accuracy rose, the same cost/reliability trade this wiki's cost page tracks,
here left unmitigated rather than countered with a boundary contract or
harness retune.

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

A concrete incident puts a dollar figure on the identity/execution gap above:
a three-person agency took a $14,000 AWS bill in a single day after attackers
extracted static access keys with unrestricted Bedrock access and burned them
invoking Claude models, and a separate case had an autonomous agent given
open-ended AWS access repeatedly reapply a CloudFormation template until it
was running far more infrastructure than the task needed. Both were caught by
a credit-card charge, not by AWS's own monitoring — billing tools like Cost
Explorer and Budgets work off data that lags roughly 24 hours, so they detect
overspend after the money is gone rather than stopping it. The fix is the same
scoped-credential, action-time-alerting discipline
[sandboxing](/topic/agent-sandboxing) already argues for, applied to spend
instead of data: IAM roles instead of static keys, service-control policies
blocking expensive instance families in agent-operated accounts, and
CloudTrail alerts on the API calls that spend money (`RunInstances`,
`InvokeModel`) rather than a budget alert that fires after the invoice.

A research architecture directly answers the "tools for certainty" framing
above with a named, layered design rather than a single fix: HALO
(Hallucination-Aware Layered Oversight) treats hallucination as a
*containable* failure mode rather than a property a bigger model will
eventually eliminate, and stacks six defenses — grounded generation over
approved content, constrained deterministic execution that bounds where the
model can err, multi-signal verification (an LLM judge plus evidence checks
against source text), calibrated abstention so the system declines rather
than guesses when grounding is thin, full traceability of every retrieval
and tool call, and continuous oversight that detects drift and regenerates
on threshold breaches. It's the identity/execution/intent split this page
already argues for, expressed as one composable architecture instead of
three separately-sourced controls.

A practitioner pattern flips the usual framing of hallucination entirely,
turning the failure mode into the mechanism: rather than asking a model to
classify text against a large, closed vocabulary it can't hold in context
(too many candidate tags or categories to enumerate in one prompt), let it
freely generate — "hallucinate" — an unconstrained guess at the right label,
then use vector-embedding similarity to snap that guess to the nearest real
entry in the vocabulary. The technique trades a classification problem the
model is bad at (picking correctly from thousands of options) for a
generation-plus-retrieval problem it's good at, and only works because the
embedding-similarity step catches and grounds the hallucination rather than
returning it as-is — a concrete instance of this page's standing "does a
hallucination widen useful context or actively mislead" question, engineered
deliberately toward the useful side instead of left to chance.

Hallucination mitigation is converging on **calibrated decoding**, not just
post-hoc detection: ReWEIGH calibrates token-level ordinal visual evidence
during decoding in vision-language models, giving the model a
candidate-specific measure of how strongly an image supports each token
rather than only judging the finished output — the same "contain it during
generation, not just catch it after" instinct HALO's constrained-execution
leg already argues for, here applied inside the decoding step itself.
AutoResearch answers the same containment question for autonomous research
agents specifically: rather than trusting a long research workflow's
automation to stay scientifically grounded, it ties insight generation back
to evidence as a design target — "insight in, hallucination out" — instead
of assuming automation alone preserves rigor.

Reliability also gets a **recursive-self-improvement caveat** rather than a
solved capability: agents can already edit their own tools, skills, and
harness, but recursive self-improvement still needs a system that can raise
the verifier alongside the agent — an unsolved half of the loop this page's
HALO and identity/execution/intent framing above doesn't yet cover, since a
self-modifying agent can also self-modify its own check.

LangSmith's Tuned Evaluators supply a user-facing complement to the standing
"prove it did the work" thread: rather than only an independent LLM judge or
a trace-mining pipeline, a Perceived Error signal lets a team find agent
mistakes directly from what users flagged in production (see [agent
evaluation](/topic/agent-evaluation) for the eval-tooling side of the same
release).

A practitioner talk packages the "tools for certainty" argument into a
concrete production discipline rather than an architecture diagram: an
LLM-powered selection system stays reliable by restricting the model's
output to a constrained schema, separating the semantic extraction step
(where the model is genuinely needed) from the deterministic code that
acts on it, and validating the model's choices with a discriminator model
before they reach the database — structuring the whole pipeline on an
MVC-style split so non-determinism is contained to one layer instead of
leaking into storage and downstream logic.

A first-party production case study puts numbers behind the identity/
execution/intent split above, from an Anthropic reliability engineer's own
incident-response practice. In the Observe phase, Claude reads logs at I/O
speed with no fatigue and catches what a human focused on error logs would
miss — during a New Year's Eve incident it flagged 4,000 accounts created
simultaneously with identical characteristics and 22-image requests each as
coordinated fraud rather than a bug, and separately root-caused a Rust
panic (a `checkpoint.rs` segment-ID validation bug) before engineers
finished reading two pages of logs by hand. The Orient phase is where it
breaks: watching request volume double alongside errors, Claude repeatedly
concluded the incident was a capacity problem needing more servers, when a
failed KV cache was the actual cause — the engineer corrected it "six,
seven times" before adding the distinction to the system prompt, and junior
engineers pointed at the same graphs are "immediately swayed" toward the
same wrong diagnosis. Postmortems come out "80% readable" but miss multiple
contributing factors and the tacit organizational knowledge behind why a
safeguard (like secondary-database fallback testing) was never built. The
unresolved risk sits a layer above both phases: if AI executes the
mitigation, humans lose the feedback loop that builds the "scar tissue"
distinguishing a senior responder from a junior one.

## What's new
An Anthropic reliability engineer's own incident-response case study puts a
concrete boundary on where LLM incident response works: superhuman at
reading logs and catching non-obvious patterns (a coordinated-fraud signal
in account-creation metadata, a Rust panic root-caused before humans
finished reading), but unable to reliably distinguish causation from
correlation on its own — misreading a KV-cache failure as a capacity
problem for "six, seven" corrections in a row — and prone to postmortems
that miss contributing factors and tacit institutional knowledge (see State
of the art above).

Prior update: A practitioner talk names a concrete production pattern for containing
non-determinism: restrict LLM output to a constrained schema, separate
semantic extraction from deterministic code, and validate choices with a
discriminator model before they reach the database — an MVC-style split
that keeps the model's fluent-but-uncertain output from leaking into
storage and downstream logic (see State of the art above).

Prior update: Recursive self-improvement gets a named caveat: agents can already edit
their own tools and harness, but the loop still needs a system that can
raise the verifier alongside the agent, since a self-modifying agent can
also self-modify its own check. Separately, ReWEIGH and AutoResearch both
push hallucination mitigation toward calibrated, in-generation containment
rather than post-hoc detection.

Prior update: A practitioner pattern deliberately generates an unconstrained guess instead
of classifying against a large closed vocabulary, then uses vector-embedding
similarity to snap that "hallucination" to the nearest real label — turning
a failure mode this page usually tracks as a risk into a designed mechanism,
grounded by the embedding step rather than returned raw (see State of the
art above).

## Why it matters for platform engineers
Reliability spans three layers platform teams have to build separately: an
identity system that can scope and audit what an agent does, an execution
substrate that survives crashes and rate limits without silently dropping
work, and an intent check that catches an agent quietly giving up or
declaring victory early. None of the three is solved by picking a better
model — they're infrastructure decisions, and skipping any one of them means
a confident-looking agent can be wrong, mid-task, or done without you
knowing which.
