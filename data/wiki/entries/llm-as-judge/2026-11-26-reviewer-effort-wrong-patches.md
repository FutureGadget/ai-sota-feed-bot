---
title: "Higher effort helps Claude 5.5 code reviewers reject wrong patches, but no setting catches them reliably"
date: 2026-11-26
theme: trusting-the-judge
evidence: [7b091d01de2f3c49]
also: [agent-reliability]
---
The study ran three Claude 5.5 models as code reviewers at low, medium, and high effort on **90** plausible-but-wrong Django patches. High effort accepted fewer wrong patches than lower settings, but no model-and-effort combination rejected them reliably.

For builders: an AI reviewer is a filter, not a gate, for patches that look right. Raising effort is worth its cost on high-risk merges. Still pair it with tests or hidden checks that exercise the behavior the patch claims to fix.
