---
title: "A CLI release broke every request behind a gateway; one-line SDK bumps shipped break and fix"
date: 2026-09-18
theme: regressions-and-reverts
evidence: [0b0904b2f918e9c9, 4e51f7285ba473b4, 8f9e2f8ba8bd1533]
---
claude-code v2.1.275 made **every request fail with a 400** on an unrecognized `advisor_20260301` input tag whenever `ANTHROPIC_BASE_URL` pointed at a proxy or gateway. v2.1.276 fixed it.

The Claude Agent SDK forwarded both: v0.2.155 carried the break and v0.2.156 the fix, each with the one-line "Updated bundled Claude CLI" changelog. Teams routing through an LLM gateway, the setup platform teams favor, were the ones broken.
