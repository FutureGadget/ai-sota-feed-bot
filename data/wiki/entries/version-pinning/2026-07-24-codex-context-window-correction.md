---
title: "Codex 0.144.6 quietly corrected bundled models' context windows to 272,000 tokens"
date: 2026-07-24
theme: transitive-pinning
evidence: [e04ae87f340863b8]
---
Codex 0.144.6 reads as a routine "refreshed bundled instructions" fix for GPT-5.6 Sol, Terra, and Luna. The same release **corrected those models' context windows to 272,000 tokens**.

Chain-deep pinning is not specific to Anthropic's stack. A pin on the CLI version alone would have carried stale bundled model metadata forward.
