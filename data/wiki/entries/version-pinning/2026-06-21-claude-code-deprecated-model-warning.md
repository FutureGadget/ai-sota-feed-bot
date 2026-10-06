---
title: "Claude Code now warns when the requested model is deprecated or auto-updated"
date: 2026-06-21
theme: compatibility-signals
evidence: [860864df5583b9ff]
---
Claude Code v2.1.183 added a **warning when the requested model is deprecated or automatically updated** to a newer one. It prints on stderr in print mode (`-p`) and also covers models set in agent frontmatter.

A model swapped out underneath a running agent becomes a visible signal an operator can schedule a migration from, instead of an unexplained behavior change. Headless jobs should capture stderr to see it.
