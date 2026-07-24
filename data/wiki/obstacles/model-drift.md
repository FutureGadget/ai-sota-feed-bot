---
slug: model-drift
kind: obstacle
title: "Agent behavior drifts as the model, SDK, and runtime churn under it"
area: drift
status: active
solutions: [version-pinning, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a, b5e2211dddab87f3, 98fe19349686f702, f038f32830795715, 2eb4a06e737c3d47, ea8bf0e5641cf4c4, f0c081fcc40a7583, cac4c9ead20e55a3, 2832f2f825db2411, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 8b71b000ca374d14, 6ffc451084feba44, 498dbb665652c50c, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, 228dddec5b6b8ab4]
updated: 2026-07-24
covers_evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a, b5e2211dddab87f3, 98fe19349686f702, f038f32830795715, 2eb4a06e737c3d47, ea8bf0e5641cf4c4, f0c081fcc40a7583, cac4c9ead20e55a3, 2832f2f825db2411, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 8b71b000ca374d14, 6ffc451084feba44, 498dbb665652c50c, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, 228dddec5b6b8ab4]
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
- **Agent SDKs** move almost daily: the Claude Agent SDK for Python ships releases whose entire changelog is "updated the bundled Claude CLI," so the executable your agent runs on changes underneath a patch-level dependency bump. That cadence has not let up: the most recent week saw the SDK roll from 0.2.115 through 0.2.120, six releases in a row advancing only the vendored CLI (2.1.206 → 2.1.211) — except one of them wasn't purely cosmetic: the 0.2.116 bump carried a CLI fix so Claude Code honors project-scoped permission grants in checkout directories, a real permission-behavior change riding on what its own changelog entry made look like just another CLI version bump. The pattern repeated two days later at larger scale: 0.2.122's changelog is again just "updated bundled Claude CLI," this time forwarding claude-code v2.1.214 — a release whose own notes list five distinct permission-check bypass fixes (a Windows PowerShell 5.1 check bypass, `docker` commands with daemon-redirect flags escaping approval, `dir/**` allow-rules over-matching outside their intended directory, long commands auto-approving past a 10,000-character threshold, and zsh variable-subscript mishandling in Bash checks). The one-line-changelog pattern hasn't slowed since: 0.2.123 forwards claude-code v2.1.215 with the same single bullet ("updated bundled Claude CLI"), and it kept recurring three releases later — 0.2.125 again reads only "updated bundled Claude CLI," this time forwarding v2.1.217 — so a team tracking only the SDK's own version number still has to open the CLI's own release notes to know what actually changed underneath it, every single release, not just occasionally. The next two releases broke from that pure-cosmetic pattern in opposite, equally consequential directions: v0.2.126 shipped real new API surface instead of just a CLI bump — `ResultMessage.terminal_reason` now surfaces why the query loop ended ("completed", "max_turns", "aborted_streaming", ...) and `ResultMessage.model_usage` gives typed per-model token/cost usage, both load-bearing for retry and cost logic built on top of the SDK — while v0.2.127 paired a genuine bug fix (`query()` no longer closes stdin on the first result frame while background tasks are still in flight) with, again, a bundled-CLI bump, this time to v2.1.219. A team that pins only the SDK version and skims changelogs for keywords can miss exactly this kind of drift.
- **Models** get deprecated out from under running agents — Claude Code now emits a warning when the requested model is deprecated, making model-upgrade drift an explicit, surfaced signal rather than a silent behavior change — and the same release hardened auto-mode safety (blocking destructive git commands), a reminder that the harness's *defaults* drift too. Claude Code v2.1.219 makes the model-upgrade case concrete rather than hypothetical: it added Claude Opus 5 (`claude-opus-5`) as the new default Opus model — 1M context, fast mode at $10/$50 per Mtok — so any code or agent that referenced "the default Opus model" now gets a different model, a larger context window, and different pricing without a single line of its own code changing.
- **Serving runtimes** drift in performance and output: vLLM v0.23.0 is another "hardening and optimization pass" on DeepSeek-V4 across backends, the kind of change that can move latency, throughput, and sampling behavior without a model swap, and the drift can be outright breaking, not just behavioral — Triton Inference Server's 2.70.0 release drops Windows support entirely and changes how its Python client handles BF16 (now requiring `ml_dtypes`), so a runtime bump can remove a deployment target or break client code that never touched the model.
- **Coding-agent CLIs regress and roll back like any other dependency**: OpenAI's Codex CLI shipped a prompting regression in its Guardian auto-review behavior, then reverted it two releases later — 0.144.2 restored the prior policy, request format, and tool behavior, followed by a version-only 0.144.3 with no further changes — the same "patch-level bump changes behavior" pattern the Claude Agent SDK bullet above describes, this time inside the auto-review policy an agent enforces rather than the CLI binary underneath it. The one-line-changelog pattern isn't Anthropic-specific either: Codex 0.144.6's changelog reads as a routine "refreshed bundled instructions" note for its GPT-5.6 Sol, Terra, and Luna models, but folded into that refresh was a correction to their context windows (272,000 tokens) — model metadata that routing and token-budget code silently depends on, changing in a point release with no separate callout.

The field is starting to give operators levers — LangGraph's CLI now supports
declaring *compatible API version ranges* — but the default posture is still
"track latest," which is exactly how drift gets in.

The **migration itself**, not just detecting drift, is a named practitioner
topic now: Google Cloud published lessons learned from accelerating
foundation-model upgrades across engineering teams, reinforcing that the
upgrade path — not just the deprecation warning — is where the drift this
page tracks actually has to be managed (see
[version pinning](/topic/version-pinning) for the specific migration case
this evidence also grounds).

## What's new
Claude Code v2.1.219 swapped the default Opus model to Claude Opus 5 — 1M
context, fast mode at $10/$50 per Mtok — the concrete default-model-swap
instance this page tracks: code or agents that referenced "the default Opus
model" now get different behavior, a larger context window, and different
pricing with no code change of their own. In the same window the Claude
Agent SDK's one-line-changelog pattern finally broke in two directions
(v0.2.126 added real API surface, v0.2.127 paired a genuine bug fix with
another bundled-CLI bump), and a competing vendor's CLI (Codex 0.144.6)
shows the identical "routine release, real metadata change underneath" shape
on its own bundled models' context windows — this obstacle isn't
Anthropic-specific.

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
