---
slug: model-drift
kind: obstacle
title: "Agent behavior drifts as the model, SDK, and runtime churn under it"
area: drift
status: active
solutions: [version-pinning, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: bundled-cli-bumps
    title: SDK bumps that hide what changed underneath
    summary: Claude Agent SDK releases routinely say only "updated bundled CLI" while the forwarded CLI carries permission-bypass fixes, new tools, or breaking changes; the SDK changelog alone is not a reliable signal.
  - key: regressions-and-reverts
    title: Regressions shipped and rolled back in point releases
    summary: Frameworks, coding-agent CLIs, and SDKs regularly ship a regression and revert it one or two releases later, so anyone who upgraded in the window got broken behavior without changing code.
  - key: model-and-default-changes
    title: Models, defaults, and prompts that change under you
    summary: Default models, reasoning effort, system prompts, context-window metadata, and review policies change on the vendor side, often silently, and pinning a version does not catch them.
  - key: serving-runtime-drift
    title: The serving runtime as a drift source
    summary: Inference-runtime upgrades move latency, sampling, and even supported platforms, and the backend alone accounts for a large share of observed benchmark variance.
  - key: drift-tooling
    title: Tools to pin, test, and replay against drift
    summary: Version ranges, intent-based versioning, cross-language tests, and cut-point replay are emerging, but the default posture across the ecosystem is still "track latest".
---

## TL;DR
An agent is built on a substrate you don't control and that moves faster than
your app: the model gets upgraded or deprecated, the agent SDK and framework
ship several releases a week, and the serving runtime changes behavior. Every
bump can silently change what the agent does, between two deploys where your
own code never changed.

## State of the art
**Every layer under the agent is a drift source.** Frameworks ship regressions
and fix them two releases later. Coding-agent CLIs change permission checks,
auto-review policy, and model metadata in point releases. Serving runtimes move
latency and sampling, and the backend alone explains a large share of
benchmark variance.

**Changelogs are not a reliable signal.** The clearest pattern is the Claude
Agent SDK: most releases say only "updated bundled CLI", while the forwarded
CLI carries permission-bypass fixes, credential-leak fixes, new tools, or a
break that took down every request behind a gateway. The same shape appears in
Codex point releases that quietly change context windows and review defaults.

**Pinning is necessary but not sufficient.** Anthropic's own Claude Code
quality postmortem traced weeks of complaints to vendor-side changes in
default reasoning effort, a caching bug, and a system-prompt line. None
touched a model or SDK version a customer could pin. Default-model swaps
(a new default Opus) do the same to anyone who referenced "the default".

**The consensus discipline** is to treat model, SDK, framework, and runtime as
pinned dependencies behind a regression gate: declared compatible version
ranges, staged upgrades, and evals before rollout. Vendors now apply the same
gate to their own prompt and default changes.

**The open problem is reproduction.** Non-deterministic inference and moving
tool state make a drift-caused failure hard to replay. Record-and-replay from a
cut point in a saved trajectory is the newest answer, but tooling is early and
"track latest" remains the ecosystem default.

## Why it matters for platform engineers
This is the obstacle that breaks an agent you already shipped, on a day you
didn't deploy. You own the agent but rent the substrate, and its release
cadence isn't yours.

Treat the model, SDK, bundled CLI, and serving runtime as pinned,
version-controlled dependencies with a regression gate (see
[version pinning](/topic/version-pinning) and
[agent benchmarks](/topic/agent-benchmarks)). Read the forwarded component's
release notes, not just the wrapper's, because security-relevant permission
changes ride there. Drift trades against freshness: the newest model or
framework is also the one most likely to move under you.
