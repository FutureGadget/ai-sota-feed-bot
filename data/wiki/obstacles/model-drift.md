---
slug: model-drift
kind: obstacle
title: "Agent behavior drifts as the model, SDK, and runtime churn under it"
area: drift
status: active
solutions: [version-pinning, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a, b5e2211dddab87f3, 98fe19349686f702, f038f32830795715, 2eb4a06e737c3d47, ea8bf0e5641cf4c4, f0c081fcc40a7583, cac4c9ead20e55a3, 2832f2f825db2411, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 8b71b000ca374d14, 6ffc451084feba44, 498dbb665652c50c, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, 228dddec5b6b8ab4, 1be544292b970eeb, b52989abd31085bd, ba2a3cbea388e94b, e2bff89776f177a1, 2db97c49b795a2d1, b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499, 3395a2bf7d5df457, d772d2f5565f338a, 74046490d599263e, 4da06896adf9ba0d]
updated: 2026-08-27
covers_evidence: [1f04aad16ad88e88, 473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, 435cc52d2f08f897, c69cda5ccda84a51, f133907eceb910d7, b78fb2c666f0c2da, 8db233accb157cb2, b44f974428f9863a, b5e2211dddab87f3, 98fe19349686f702, f038f32830795715, 2eb4a06e737c3d47, ea8bf0e5641cf4c4, f0c081fcc40a7583, cac4c9ead20e55a3, 2832f2f825db2411, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 8b71b000ca374d14, 6ffc451084feba44, 498dbb665652c50c, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, 228dddec5b6b8ab4, 1be544292b970eeb, b52989abd31085bd, ba2a3cbea388e94b, e2bff89776f177a1, 2db97c49b795a2d1, b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499, 3395a2bf7d5df457, d772d2f5565f338a, 74046490d599263e, 4da06896adf9ba0d]
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
- **Agent SDKs** move almost daily: the Claude Agent SDK for Python ships releases whose entire changelog is "updated the bundled Claude CLI," so the executable your agent runs on changes underneath a patch-level dependency bump. That cadence has not let up: the most recent week saw the SDK roll from 0.2.115 through 0.2.120, six releases in a row advancing only the vendored CLI (2.1.206 → 2.1.211) — except one of them wasn't purely cosmetic: the 0.2.116 bump carried a CLI fix so Claude Code honors project-scoped permission grants in checkout directories, a real permission-behavior change riding on what its own changelog entry made look like just another CLI version bump. The pattern repeated two days later at larger scale: 0.2.122's changelog is again just "updated bundled Claude CLI," this time forwarding claude-code v2.1.214 — a release whose own notes list five distinct permission-check bypass fixes (a Windows PowerShell 5.1 check bypass, `docker` commands with daemon-redirect flags escaping approval, `dir/**` allow-rules over-matching outside their intended directory, long commands auto-approving past a 10,000-character threshold, and zsh variable-subscript mishandling in Bash checks). The one-line-changelog pattern hasn't slowed since: 0.2.123 forwards claude-code v2.1.215 with the same single bullet ("updated bundled Claude CLI"), and it kept recurring three releases later — 0.2.125 again reads only "updated bundled Claude CLI," this time forwarding v2.1.217 — so a team tracking only the SDK's own version number still has to open the CLI's own release notes to know what actually changed underneath it, every single release, not just occasionally. The next two releases broke from that pure-cosmetic pattern in opposite, equally consequential directions: v0.2.126 shipped real new API surface instead of just a CLI bump — `ResultMessage.terminal_reason` now surfaces why the query loop ended ("completed", "max_turns", "aborted_streaming", ...) and `ResultMessage.model_usage` gives typed per-model token/cost usage, both load-bearing for retry and cost logic built on top of the SDK — while v0.2.127 paired a genuine bug fix (`query()` no longer closes stdin on the first result frame while background tasks are still in flight) with, again, a bundled-CLI bump, this time to v2.1.219. A team that pins only the SDK version and skims changelogs for keywords can miss exactly this kind of drift. The pure-cosmetic pattern then resumed at pace: v0.2.130 and v0.2.131 are each again a single "updated bundled Claude CLI" line (forwarding v2.1.222, then v2.1.223) with no other changes disclosed — but the CLI release riding underneath one of those bumps, v2.1.221, is not cosmetic at all: it fixes a Bash permission-check bypass where zsh could execute hidden commands inside `[[ ]]` regex conditionals, a Windows PowerShell permission check mishandling quoted paths, and adds a `mode: "mask"` sandbox setting so sandboxed commands read a sentinel credential file while a proxy substitutes the real value only on egress — the same "permission-bypass fixes hidden inside a one-line SDK changelog" shape the v2.1.214 case already established, recurring on a different CLI version. A fourth wave, three weeks later, is the largest yet: four more one-line "updated bundled Claude CLI" releases (v0.2.135, v0.2.136, v0.2.138, v0.2.139) forward CLI v2.1.227, v2.1.228, v2.1.232, and v2.1.233 respectively, and three of those four CLI releases carry undisclosed security fixes — v2.1.227 alone fixes four issues (a crafted-command Bash permission-check bypass, tab/invisible-Unicode characters that hid parts of a command from the approval dialog, a workflow-sandbox escape via dynamic `import()`, and an agent-definition `bypassPermissions` mode that ignored an org's disable policy), v2.1.232 fixes a PowerShell bypass (variable-writing parameters silently overwriting `$PSDefaultParameterValues`) and a Windows Git Bash bypass (Cygwin-style symlinks evading path validation), and v2.1.233 closes an NTLM credential-leak vector where a Windows NT `\??\` device-prefix path bypassed UNC path validation. The one release in between, v2.1.228, hardens skills synced from claude.ai so they no longer shadow local commands or MCP prompts and can no longer run `!` shell commands or expand `@` file references from their body — a supply-chain-shaped fix for synced, not locally-authored, content. Four waves of "permission-bypass fixes hidden inside a one-line SDK changelog" in two months is no longer an anomaly in this dependency's release shape; it's the default one. A fifth wave, a week later, forwards on two different axes at once: v0.2.143 and v0.2.144 are each again a single "updated bundled Claude CLI" line, forwarding claude-code v2.1.238 and v2.1.246 respectively, and v2.1.238 continues the specific recurring theme the v2.1.221 case established — Claude Code "improved Bash tool permission checking for zsh-specific syntax in shell conditionals," another patch to the same class of zsh-conditional loophole rather than a one-off — while v2.1.246 pairs a real permission-check bypass fix (Bash commands with a malformed dangling `&&` or `||` operator now always require approval, closing a path that could previously skip the prompt) with a credential-leak fix (telemetry and metrics requests no longer carry the API key configured for a third-party `ANTHROPIC_BASE_URL` gateway to the wrong host) and a sandbox fix (the command sandbox's filesystem configuration now respects `--setting-sources`), plus a startup warning that Bash allow rules with a wildcard before the subcommand (e.g. `Bash(git * main)`) also match options inserted before it — a permission-rule-matching pitfall surfaced for operators rather than silently closed. v0.2.145, forwarding v2.1.247, breaks the pattern in the opposite direction again, the same way v0.2.126 did months earlier: its own SDK changelog is still just "updated bundled Claude CLI," but the CLI underneath ships real new capability — a `SendFeedback` tool and a `/claude-api cost-optimize` skill — with no hint of either in the SDK's own release notes.
- **Community tooling is starting to treat this obstacle as its own category**: Drift, an open-source, intent-driven versioning tool for AI coding agents, frames exactly the problem this bullet documents — that an agent's behavior can shift between ordinary-looking releases — as something a team should version and diff explicitly, rather than discover after the fact from a changelog line that undersells what changed.
- **Models** get deprecated out from under running agents — Claude Code now emits a warning when the requested model is deprecated, making model-upgrade drift an explicit, surfaced signal rather than a silent behavior change — and the same release hardened auto-mode safety (blocking destructive git commands), a reminder that the harness's *defaults* drift too. Claude Code v2.1.219 makes the model-upgrade case concrete rather than hypothetical: it added Claude Opus 5 (`claude-opus-5`) as the new default Opus model — 1M context, fast mode at $10/$50 per Mtok — so any code or agent that referenced "the default Opus model" now gets a different model, a larger context window, and different pricing without a single line of its own code changing.
- **Serving runtimes** drift in performance and output: vLLM v0.23.0 is another "hardening and optimization pass" on DeepSeek-V4 across backends, the kind of change that can move latency, throughput, and sampling behavior without a model swap, and the drift can be outright breaking, not just behavioral — Triton Inference Server's 2.70.0 release drops Windows support entirely and changes how its Python client handles BF16 (now requiring `ml_dtypes`), so a runtime bump can remove a deployment target or break client code that never touched the model. A controlled study puts a number on how much of that drift is the backend alone, isolated from the model: crossing three instruction-tuned models against five inference frameworks (HuggingFace, vLLM, Ollama, and others) and six benchmarks under deterministic, sampling-noise-free decoding, the serving backend explains roughly 39% of the score variance a practitioner sees out of the box — meaning "which inference framework and version produced this number" belongs next to "which model" as a variable a team pins and discloses, not one it can treat as non-influential plumbing (see [agent evaluation](/topic/agent-evaluation) for the same finding from the benchmarking-pipeline side).
- **Coding-agent CLIs regress and roll back like any other dependency**: OpenAI's Codex CLI shipped a prompting regression in its Guardian auto-review behavior, then reverted it two releases later — 0.144.2 restored the prior policy, request format, and tool behavior, followed by a version-only 0.144.3 with no further changes — the same "patch-level bump changes behavior" pattern the Claude Agent SDK bullet above describes, this time inside the auto-review policy an agent enforces rather than the CLI binary underneath it. The one-line-changelog pattern isn't Anthropic-specific either: Codex 0.144.6's changelog reads as a routine "refreshed bundled instructions" note for its GPT-5.6 Sol, Terra, and Luna models, but folded into that refresh was a correction to their context windows (272,000 tokens) — model metadata that routing and token-budget code silently depends on, changing in a point release with no separate callout. The same CLI's auto-review policy drifted again, in the opposite direction from the earlier regression-and-revert: 0.146.1 backported "safer automatic-review defaults for cyber-capable models," tightening the guardrail behavior an agent enforces on models flagged for cyber capability — a policy change delivered as a routine bugfix release, the same shape as the earlier Guardian regression but reflecting the same cyber-eval-incident pressure now showing up on the [prompt injection](/topic/prompt-injection) and [agent evaluation](/topic/agent-evaluation) pages.

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
A fifth wave of the Claude Agent SDK's one-line-changelog pattern forwards on
two axes at once: v0.2.144 ("updated bundled Claude CLI," nothing else)
forwards claude-code v2.1.246, which hides a real permission-check bypass fix
(malformed dangling `&&`/`||` Bash operators no longer skip the approval
prompt) alongside a credential-leak fix (third-party-gateway API keys no
longer reach Anthropic's telemetry endpoint) and a sandbox filesystem-config
fix. v0.2.143 forwards v2.1.238, which continues the same recurring
zsh-shell-conditional permission-check theme the v2.1.221 case established,
and v0.2.145 forwards v2.1.247, which flips the pattern the other way —
shipping a real `SendFeedback` tool and a `/claude-api cost-optimize` skill
under the same cosmetic SDK bump.

Prior update: A fourth wave of the same pattern was the largest yet: four
releases (v0.2.135, v0.2.136, v0.2.138, v0.2.139) each read only "updated
bundled Claude CLI," but three of the four CLI versions they forward carry
undisclosed security fixes — v2.1.227 alone fixes four permission-check
bypasses, v2.1.232 fixes a PowerShell and a Windows Git Bash bypass, and
v2.1.233 closes an NTLM credential-leak vector. A new open-source tool,
Drift, is now framing this exact obstacle — behavior shifting between
ordinary-looking releases — as something to version and diff explicitly.

Prior update: A controlled study names a drift source this page hadn't isolated before:
holding the model fixed and varying only the inference framework (HuggingFace,
vLLM, Ollama, and others) under deterministic decoding, the serving backend
alone accounts for roughly 39% of the score variance a practitioner sees —
evidence that framework/version identity, not just model version, has to be
pinned and disclosed to make a benchmark number reproducible.

Prior update: The Claude Agent SDK's one-line-changelog pattern (v0.2.130, v0.2.131 —
each just "updated bundled Claude CLI") again hid a substantive change
underneath: the CLI version it forwards, v2.1.221, fixes two permission-check
bypasses (a zsh `[[ ]]` regex conditional bypass, a Windows PowerShell
quoted-path bypass) and adds a sandboxed-credential masking mode — the same
"real change, cosmetic SDK changelog" shape the v2.1.214 case established
weeks earlier, recurring on a different release. On the competing-vendor
side, Codex CLI 0.146.1 backported "safer automatic-review defaults for
cyber-capable models," a guardrail-policy drift delivered as a routine
bugfix release rather than a version bump a team would think to review.

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
