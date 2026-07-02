---
slug: version-pinning
kind: solution
title: "Version pinning, compatibility ranges, and staged upgrades"
status: active
obstacles: []
related_storylines: []
evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 246a4c93052ef3c1]
updated: 2026-07-02
covers_evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 246a4c93052ef3c1]
---

## TL;DR
Treat the model, agent SDK, framework, and serving runtime as version-controlled
dependencies, not a rolling stream: pin exact versions, declare the compatibility
range you actually support, heed deprecation warnings, and promote upgrades
through a staged, tested path instead of tracking latest. It doesn't stop the
substrate from changing — it stops the change from reaching production
unnoticed.

## State of the art
The primitives are arriving. **Compatibility ranges** let you state the
substrate versions an agent is built against rather than implicitly accepting
whatever is newest — LangGraph's CLI added support for declaring compatible API
version ranges, turning an implicit assumption into an explicit, checkable
contract. **Deprecation signals** close the gap where a model vanishes underneath
a running agent: Claude Code now warns when the requested model is deprecated, so
an operator can schedule the migration instead of discovering it as an outage.
**Transitive pinning** is the subtle case the agent SDKs expose — a Claude Agent
SDK release whose only change is bumping the bundled CLI shows that pinning your
direct dependency is not enough when that dependency vendors an executable; the
version you actually run can move at a patch bump, so the pin has to reach the
whole chain (SDK → bundled CLI → model). A single recent week makes the point
quantitatively: the SDK went 0.2.105 → 0.2.110 with each release advancing only
the vendored CLI (2.1.183 → 2.1.191), so a lockfile that pinned `claude-agent-sdk`
but not its bundled binary would have let the executable drift roughly daily —
exactly the gap a chain-deep pin closes. The honest current state is that the
tooling gives you the levers but the defaults still favor latest, so pinning is a
discipline you impose, not a default you inherit.

**Pinning the default matters as much as pinning the version**: when a
harness release swaps its default model — Claude Code moving to Claude
Sonnet 5, with a 1M-token context window and different promotional pricing
— any agent that relied on "whatever the harness defaults to" rather than
an explicit model id inherits a new context budget and price the day that
release ships. The pin has to name the model explicitly, not just the
SDK/CLI version, or "pinned" silently stops meaning what you thought.

## What's new
A concrete case for pinning the *model id itself*, not just the SDK/CLI: a
Claude Code release changed its default model to Claude Sonnet 5 (1M-token
context, new promotional pricing), so any agent relying on the harness
default rather than an explicit model pin picked up a different context
budget and price with no code change of its own.

Two concrete levers landed: declarable compatible API version ranges (LangGraph
CLI) and explicit deprecation warnings for requested models (Claude Code) —
moving drift management from "hope the upgrade is safe" toward stating the
contract and being told before it breaks.

## Trade-offs
Pinning trades freshness and security currency for stability: stay pinned too
long and you miss fixes, performance passes, and patched vulnerabilities, and you
accumulate a painful catch-up upgrade. Pin too loosely and a patch bump
reintroduces a regression. Ranges and staged rollouts add CI and release
machinery, and a pin is only as good as the regression suite that gates the
unpin — without [agent benchmarks](/topic/agent-benchmarks) you've frozen the
version but not proven the behavior.

## Why it matters for platform engineers
This is ordinary dependency hygiene applied to a substrate most teams treat as a
service rather than a dependency. The deliverable is a lockfile that reaches all
the way down — model id, SDK, bundled CLI, framework, serving runtime — plus a
staged upgrade path gated by regression evals, so a model deprecation or a
framework patch is a planned migration, not a surprise behavior change in prod.
It pairs directly with [model drift](/topic/model-drift): pinning is how you
decide *when* drift reaches you instead of letting it arrive on the substrate's
schedule.
