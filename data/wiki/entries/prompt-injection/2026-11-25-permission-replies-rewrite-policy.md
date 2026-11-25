---
title: "A permission-prompt answer can delete deny rules, turning prompt relays into policy administrators"
date: 2026-11-25
theme: agent-authorization
evidence: [6bdcd0c1ace0da2f]
also: [agent-sandboxing]
---
The paper shows that Claude Code checks only permission updates that **add or replace allow rules**. A remote service answering an unrelated prompt can attach an update that **deletes** the deny rule protecting secrets; the agent then reads them in that session and the next, even sandboxed. The deletion leaves the same record as a local operator edit, so the runtime cannot tell who wrote the rule.

The authors prove two tight bounds: a runtime without rule authorship may accept only updates that keep every denied call denied; one that records authorship may let each party remove only its own restrictions. They predicted outcomes in **13 permission designs in 10 agent systems**. For builders: record who wrote each policy rule, and validate deletions at the shared update step.
