---
title: "Intent contracts keep users' tasks intact under planner over-reach but do not reduce unauthorized actions"
date: 2026-11-19
theme: agent-authorization
evidence: [b14444f3542c6a60]
---
In intent contracts the planning model holds **no tools**. Each step it submits a logged contract (goal, verbatim user quote, scope), code validates it, and a small trusted model checks it against the user's words and writes the tool call itself.

On three AmPermBench families, when the planner adds unrequested work, contracts still complete the user's task in **27/30** runs against **16/30** for a reviewer that can only refuse whole commands. But contracts do not reduce unauthorized actions versus blind review: state-changing runs hit a wrong target **40-49%** of the time, because the planner picks the wrong object for an ambiguous reference and no trusted model can see the environment to catch it. For builders: authorization layers fix scope, not target resolution.
