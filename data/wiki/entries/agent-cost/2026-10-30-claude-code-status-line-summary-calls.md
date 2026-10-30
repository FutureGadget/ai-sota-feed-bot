---
title: "Claude Code re-sends each background agent's full transcript every ~30s for a status line"
date: 2026-10-30
theme: harness-and-context
evidence: [94430ceaa839cbc6, 4d9b58b182c3fddf]
---
A reverse-engineering gist (Claude Code 2.1.257-2.1.312, binary unmodified, community-reported, not confirmed by Anthropic) finds that every ~30 seconds each background agent's **entire transcript** goes to that agent's own model, usually Opus, with the prompt "describe your most recent action in 3-5 words". The answer only updates the agents panel; it never reaches the conversation.

It is reportedly on by default since 2.1.232 with no setting to disable it. A second write-up prices one call at Opus 5.5 list rates. Cost grows with transcript length times agent count, so long-lived fleets pay most. Check harness-side housekeeping calls in your own usage logs, not just task prompts.
