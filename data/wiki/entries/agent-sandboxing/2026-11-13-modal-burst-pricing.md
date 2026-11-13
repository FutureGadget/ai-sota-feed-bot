---
title: "Modal bills sandboxes on actual use: a typical one sits under 6% of peak CPU for half its life"
date: 2026-11-13
theme: managed-platforms
evidence: [86cff174db20bc69]
also: [agent-cost]
---
Modal reports that a typical sandbox spends more than half its life below 6% of its peak CPU: a coding agent idles while the model reasons and spikes on installs, tests, and builds.

Modal sandboxes now burst by default. Each starts at a 0.125-core, 128 MiB request, draws from idle machine capacity when work spikes, and is billed each second for the higher of its request and its actual use. An optional limit caps the burst.

Modal's worked example, a 20-minute coding-agent task, averages 0.44 CPU against a 6-CPU peak and costs 8.4¢ per sandbox-hour versus 20¢ for a fixed reservation, a 58% saving. The example is illustrative, not a production trace; all figures are vendor-reported. Estimate sandbox cost from average use, not peak.
