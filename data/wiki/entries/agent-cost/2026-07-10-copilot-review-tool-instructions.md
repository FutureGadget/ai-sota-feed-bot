---
title: "Rewriting tool instructions, not tools, cut Copilot code review cost ~20%"
date: 2026-07-10
theme: harness-and-context
evidence: [c8dc1df614610019]
---
When GitHub moved Copilot code review onto shared Unix-style tools (`grep`/`glob`/`view`), **average cost went up**. The tools' instructions invited the broad, exploratory browsing that suits an interactive assistant, not the narrow, diff-anchored search a reviewer needs.

Rewriting the instructions to start from the diff, batch searches before reading, and read only the needed line ranges cut **average review cost about 20%** while holding review quality. A tool's instructions are as much a cost surface as its schema.
