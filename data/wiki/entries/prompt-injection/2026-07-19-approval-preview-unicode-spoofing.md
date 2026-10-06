---
title: "Claude Code fixes approval previews that injected Unicode could make show a different command"
date: 2026-07-19
theme: harness-controls
evidence: [8eafdf1e65e79a0b]
---
Claude Code v2.1.211 fixes permission previews relayed to chat channels that didn't neutralize **bidirectional-override, zero-width, and look-alike quote characters**. Injected tool input could make an approval message display a safer-looking command than the one that would actually run.

The human approval step is itself an injectable channel. Anything a person is meant to trust as ground truth (approval prompts, diffs, previews) needs the same sanitization as model input.
