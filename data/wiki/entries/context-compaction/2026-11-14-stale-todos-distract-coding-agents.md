---
title: "Stale TODOs and obsolete docs pull coding agents into side-quests, measurable from traces"
date: 2026-11-14
theme: curating-the-working-set
evidence: [370ba7508446141c]
also: [grounding]
---
A Google engineering post argues that what humans skim past in a codebase, agents treat as a call to action. Obsolete specs, resolved bugs, and lagging docs enter context during research. At best they cost tokens, steps, and time; at worst they ground the agent on false facts.

The measurement trick: inline `TODO(bug/...)` comments are a proxy. The team cross-references every TODO an agent reads against the linked bug's status and the user's prompt. That separates valid work from wasted detours automatically, across distributed traces covering hundreds of millions of agent steps.

For builders: stale repo text is a context-quality problem, not only a hygiene one. Linked tickets give you a machine-checkable signal of which in-repo instructions are dead.
