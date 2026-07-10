---
slug: model-drift
kind: obstacle
title: "Agent behavior drifts as the model, SDK, and runtime churn under it"
area: drift
status: active
solutions: [version-pinning, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a]
updated: 2026-07-10
covers_evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a]
---

## TL;DR
An agent is built on a substrate you don't control and that moves faster than
your app: the underlying model gets upgraded or deprecated, the agent SDK and
orchestration framework ship multiple releases a week, and the serving runtime
changes its behavior under load. Every bump can silently change what the agent
does — or reintroduce a regression — between two deploys where *your* code never
changed. Drift is the run-time obstacle of maintenance: keeping a working agent
working as everything beneath it shifts.

## State of the art
The substrate churns across several layers, and each is a drift source:

- **Frameworks** ship fast and regress: LangGraph 1.2.6 had to fix nested subgraphs inheriting the parent checkpoint namespace — a regression introduced two releases earlier in 1.2.3 — meaning anyone who upgraded into that window silently got broken checkpointing without touching their own code.
- **Agent SDKs** move almost daily: the Claude Agent SDK for Python ships releases whose entire changelog is "updated the bundled Claude CLI," so the executable your agent runs on changes underneath a patch-level dependency bump. That cadence has not let up: in a single recent week the SDK rolled from 0.2.105 through 0.2.110, every release doing nothing but advancing the bundled CLI (2.1.183 → 2.1.191), while the CLI itself shipped its own stream of patch releases (claude-code 2.1.190, "bug fixes and reliability improvements") — so a team that pinned only the SDK version still saw the binary under it move roughly daily.
- **Models** get deprecated out from under running agents — Claude Code now emits a warning when the requested model is deprecated, making model-upgrade drift an explicit, surfaced signal rather than a silent behavior change — and the same release hardened auto-mode safety (blocking destructive git commands), a reminder that the harness's *defaults* drift too.
- **Serving runtimes** drift in performance and output: vLLM v0.23.0 is another "hardening and optimization pass" on DeepSeek-V4 across backends, the kind of change that can move latency, throughput, and sampling behavior without a model swap, and the drift can be outright breaking, not just behavioral — Triton Inference Server's 2.70.0 release drops Windows support entirely and changes how its Python client handles BF16 (now requiring `ml_dtypes`), so a runtime bump can remove a deployment target or break client code that never touched the model.

The field is starting to give operators levers — LangGraph's CLI now supports
declaring *compatible API version ranges* — but the default posture is still
"track latest," which is exactly how drift gets in.

## What's new
Drift testing gains a **cross-language** axis: LangDrift asserts tool
selection, arguments, and response language deterministically across
locales at a fixed agent endpoint, and found several non-English locales
(Basque, Yoruba, Swahili, Chinese, Welsh, Mongolian) triggering wrong-tool or
missing-argument failures across multiple independently trained models —
evidence that a passing English regression suite says nothing about drift
the agent already has in other locales.

## Why it matters for platform engineers
This is the obstacle that breaks an agent you already shipped, on a day you
didn't deploy. You own the agent but rent the substrate, and its release cadence
isn't yours — a framework patch can reintroduce a regression, an SDK bump can
swap the executable, and a model deprecation can change behavior or pull the
model entirely. The discipline is to treat the model, SDK, and serving runtime as
pinned, version-controlled dependencies with a regression gate
(see [version pinning](/topic/version-pinning) and
[agent benchmarks](/topic/agent-benchmarks)) — staged, tested upgrades, not a
rolling "latest." Drift trades against freshness: the newest model or framework
is also the one most likely to move under you.
