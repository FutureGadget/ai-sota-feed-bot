---
slug: version-pinning
kind: solution
title: "Version pinning, compatibility ranges, and staged upgrades"
status: active
obstacles: []
related_storylines: []
evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 8db233accb157cb2, 498dbb665652c50c]
updated: 2026-07-16
covers_evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 8db233accb157cb2, 498dbb665652c50c]
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
quantitatively: the SDK went 0.2.115 → 0.2.120 with each release advancing only
the vendored CLI (2.1.206 → 2.1.211), so a lockfile that pinned `claude-agent-sdk`
but not its bundled binary would have let the executable drift roughly daily —
exactly the gap a chain-deep pin closes. The honest current state is that the
tooling gives you the levers but the defaults still favor latest, so pinning is a
discipline you impose, not a default you inherit.

Pinning also has to account for **known-vulnerable** versions, not just
behavioral drift: deptrust checks an agent's resolved package versions across
npm, PyPI, crates.io, Go modules, and other ecosystems against vulnerability
databases, so a pin (or an upgrade) can be validated as safe, not just as
consistent.

Staying pinned only helps if the eventual **upgrade itself** is tractable, and
a practitioner account of migrating a product between foundation models finds
the naive path doesn't scale: converting hand-built discovery guidelines into
a fixed automated conversion script gave quick wins but was too rigid for
different data formats and edge cases. Replacing the rigid script with a
flexible agent — one that analyzes the data and adapts its own prompts per
project instead of following one fixed workflow, graded by model-based
autoraters instead of manual review — cut a video-translation migration from
months to hours. It's the same "regression-gated, not rolling-latest" upgrade
discipline this page argues for, aimed at the migration process itself rather
than just the target version.

## What's new
A pinning check now targets **supply-chain safety** specifically: deptrust
scans an agent's resolved dependencies across a dozen ecosystems for known
vulnerabilities, complementing behavioral-regression pinning (compatible API
version ranges in LangGraph's CLI, Claude Code's deprecation warnings) with a
security-focused version check. Separately, a practitioner migration write-up
shows *how* to make the eventual upgrade itself tractable: swap a rigid,
hand-scripted conversion pipeline for a flexible agent graded by autoraters,
cutting a real foundation-model migration from months to hours.

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
