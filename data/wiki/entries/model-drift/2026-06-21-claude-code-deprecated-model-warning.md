---
title: "Claude Code warns when the requested model is deprecated or auto-updated"
date: 2026-06-21
theme: model-and-default-changes
evidence: [860864df5583b9ff]
---
claude-code v2.1.183 warns when the **requested model is deprecated or automatically updated to a newer one**, on stderr in print mode and for models set in agent frontmatter. The same release blocks destructive git commands and `terraform`/`pulumi`/`cdk destroy` in auto mode unless asked.

A silent model swap becomes a visible signal. The harness's safety defaults also moved in the same release.
