---
title: "Codex ships an auto-review prompting regression, then reverts it in a point release"
date: 2026-07-13
theme: regressions-and-reverts
evidence: [b5e2211dddab87f3, 98fe19349686f702]
---
Codex 0.144.2 **restored the previous Guardian auto-review policy**, request format, and tool behavior after rolling back a prompting regression. 0.144.3 followed as a version-only release with no changes.

The drift sat inside the auto-review policy the agent enforces, not the model or the binary. A patch-level bump changed safety behavior twice in two releases.
