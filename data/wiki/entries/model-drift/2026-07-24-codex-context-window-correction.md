---
title: "A Codex point release quietly corrects GPT-5.6 context windows to 272K"
date: 2026-07-24
theme: model-and-default-changes
evidence: [e04ae87f340863b8]
---
Codex 0.144.6 reads as a routine refresh of bundled instructions for GPT-5.6 Sol, Terra, and Luna, but it also **corrects their context windows to 272,000 tokens**.

Routing and token-budget code depends on that metadata, and it changed in a point release without a separate callout. The one-line-changelog problem is not specific to one vendor.
