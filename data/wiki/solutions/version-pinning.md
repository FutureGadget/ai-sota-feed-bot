---
slug: version-pinning
kind: solution
title: "Version pinning, compatibility ranges, and staged upgrades"
status: active
obstacles: []
related_storylines: []
evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 8db233accb157cb2, 498dbb665652c50c, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 6ffc451084feba44, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499, 3395a2bf7d5df457]
updated: 2026-08-15
covers_evidence: [473efa3d40555ca9, 860864df5583b9ff, 0971e4ffff50b51c, c69cda5ccda84a51, 8db233accb157cb2, 498dbb665652c50c, fe9e50bf2d5b21fe, fc682cd69e9ef51b, 6ffc451084feba44, a19f1341e900df0e, 90726831e1877773, e04ae87f340863b8, b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499, 3395a2bf7d5df457]
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
exactly the gap a chain-deep pin closes. The stakes of that gap went up two days
later: SDK 0.2.122 was again a one-line "bundled CLI update," but the CLI it
carried forward (v2.1.214) fixed five separate permission-check bypasses — a
lockfile pinning only the SDK version would have silently accepted (or, read
the other way, silently missed) five security-relevant behavior changes at
once. The pattern has since held for three further releases in a row (SDK
0.2.123 → 0.2.125, each forwarding only a bundled-CLI version bump), so a
chain-deep pin is not a one-time fix for a single incident but a standing
requirement every release repeats. The next two releases show pinning has to
track more than just the bundled CLI, too: v0.2.126 added real, pinnable API
surface on its own patch bump — `ResultMessage.terminal_reason` and typed
`ResultMessage.model_usage` — so an integration that pins the SDK version
also has to decide when to adopt behavior that only exists past that exact
patch; v0.2.127 then shipped a genuine bug fix (background tasks no longer
have `query()`'s stdin closed out from under them) bundled with yet another
CLI bump, to v2.1.219, meaning a pin held one version too early keeps a real
defect as well as missing a CLI update. The chain-deep pinning problem is
also not specific to Anthropic's stack: Codex 0.144.6's changelog reads as a
routine "refreshed bundled instructions" note, but the same release quietly
corrected its bundled GPT-5.6 Sol/Terra/Luna models' context windows to
272,000 tokens — a pin on the CLI version alone would have silently carried
stale model metadata forward. A fourth wave of chain-deep bundled-CLI bumps
(SDK v0.2.135 → v0.2.139) makes the case at its largest scale yet: three of
the four CLI versions forwarded across those four "no other changes" SDK
releases carry undisclosed security fixes — v2.1.227 alone fixes four
permission-check bypasses, v2.1.232 fixes a PowerShell and a Windows Git Bash
bypass, and v2.1.233 closes an NTLM credential-leak vector — so a lockfile
that pinned only the SDK's own version number would have accepted or missed
seven distinct security-relevant behavior changes across four "cosmetic"
releases. The honest current state is that the
tooling gives you the levers but the defaults still favor latest, so pinning is a
discipline you impose, not a default you inherit.

The obstacle itself is starting to attract **purpose-built tooling** rather
than being handled purely with lockfiles and CI gates: Drift is an
open-source, intent-driven versioning tool for AI coding agents built to
version and diff an agent's behavior explicitly across releases — the same
instinct this page's chain-deep pinning discipline serves, packaged as a
dedicated tool rather than a discipline a team has to invent for itself.

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
A fourth, largest-yet wave of chain-deep bundled-CLI bumps (SDK v0.2.135 →
v0.2.139, four releases each reading only "updated bundled Claude CLI")
shows a version-only pin missing three of four CLI versions forwarded — and
those three carry seven distinct undisclosed security fixes between them
(four permission-check bypasses in v2.1.227, two more in v2.1.232, an NTLM
credential-leak vector closed in v2.1.233). A new open-source tool, Drift,
is now packaging this page's chain-deep-pinning discipline as a dedicated
product rather than something each team re-invents.

Prior update: Pinning now has to track more than bundled-CLI churn: SDK v0.2.126 added
genuinely new pinnable API surface (`terminal_reason`, typed `model_usage`)
on an ordinary patch bump, and v0.2.127 shows a pin held one version early
also keeps a real stdin-closure bug alongside missing the CLI update to
v2.1.219 — a version-only lockfile can't tell "safe to skip" releases from
"actually changed" ones. Codex 0.144.6 shows the same chain-deep pinning
gap on a competing vendor's stack, quietly correcting bundled models'
context windows (272,000 tokens) inside a release billed as a routine
instructions refresh.

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
