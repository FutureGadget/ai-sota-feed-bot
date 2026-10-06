---
title: "Claude Code makes Opus 5 the default Opus model"
date: 2026-07-24
theme: model-and-default-changes
evidence: [228dddec5b6b8ab4]
---
claude-code v2.1.219 adds **Claude Opus 5 (`claude-opus-5`) as the new default Opus model**: 1M context, fast mode at $10/$50 per Mtok.

Anything that referenced "the default Opus model" now gets a different model, a larger context window, and different pricing without a code change. Pin explicit model IDs where behavior or cost matters.
