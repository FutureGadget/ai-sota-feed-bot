---
slug: version-pinning
kind: solution
title: "Version pinning, compatibility ranges, and staged upgrades"
status: active
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: transitive-pinning
    title: Pinning the whole chain, not just the SDK
    summary: Agent SDK patch releases routinely forward bundled CLI and model-metadata changes, including permission fixes, so a pin must reach SDK, bundled CLI, and model to mean anything.
  - key: compatibility-signals
    title: Compatibility ranges and deprecation signals
    summary: Frameworks now let you declare supported API version ranges, and agent CLIs warn when a requested model is deprecated or auto-updated, turning silent substrate changes into checkable signals.
  - key: upgrade-tooling
    title: Tooling for safe pins and tractable upgrades
    summary: Vulnerability checks on agent-chosen versions, agentic model-migration pipelines graded by autoraters, and early behavior-versioning tools make pins safer and upgrades cheaper.
---

## TL;DR
Treat the model, agent SDK, framework, and serving runtime as version-controlled
dependencies, not a rolling stream: pin exact versions, declare the
compatibility range you support, heed deprecation warnings, and promote
upgrades through a staged, tested path instead of tracking latest. It doesn't
stop the substrate from changing; it stops the change reaching production
unnoticed.

## State of the art
**The levers exist, but defaults still favor latest.** Pinning is a discipline
you impose, not one you inherit.

**Pins have to reach the whole chain.** The clearest lesson comes from agent
SDKs that vendor an executable. Claude Agent SDK releases often list only
"updated bundled CLI", yet the forwarded CLI can carry permission-check fixes,
and one patch release fixed background tasks silently skipping PreToolUse
hooks. Codex showed the same on another vendor's stack, correcting bundled
models' context windows inside a release billed as an instructions refresh. A
lockfile that pins the SDK alone cannot tell a cosmetic bump from a
security-relevant one.

**Compatibility signals are arriving.** LangGraph's CLI accepts declared API
version ranges, and Claude Code warns when a requested model is deprecated or
auto-updated. Both turn a silent substrate change into something CI or an
operator can act on.

**Upgrade tooling is the newer front.** Vulnerability checks on resolved
versions (deptrust) make a pin safe, not just consistent. Google Cloud cut a
model migration from months to hours by replacing a rigid conversion script
with an adaptive agent graded by autoraters. Dedicated behavior-versioning
tools such as Drift are appearing but unproven.

**The open problem is reading the changelog chain.** Nothing yet surfaces,
automatically, which transitive bump changed behavior or security posture;
teams still diff release notes by hand.

## Trade-offs
Pinning trades freshness and security currency for stability. Stay pinned too
long and you miss fixes, including permission and hook-bypass fixes shipped as
"internal" bumps, and you build up a painful catch-up upgrade. Pin too loosely
and a patch bump reintroduces a regression. Ranges and staged rollouts add CI
and release machinery. A pin is only as good as the regression suite that
gates the unpin: without [agent benchmarks](/topic/agent-benchmarks) you have
frozen the version but not proven the behavior.

## Why it matters for platform engineers
This is ordinary dependency hygiene applied to a substrate most teams treat as
a service. The deliverable is a lockfile that reaches all the way down (model
id, SDK, bundled CLI, framework, serving runtime) plus a staged upgrade path
gated by regression evals, so a model deprecation or framework patch is a
planned migration, not a surprise in prod. It pairs with
[model drift](/topic/model-drift): pinning decides *when* drift reaches you
instead of letting it arrive on the vendor's schedule.
