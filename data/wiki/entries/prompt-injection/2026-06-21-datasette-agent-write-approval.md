---
title: "datasette-agent gates database writes behind user approval and the user's own permissions"
date: 2026-06-21
theme: harness-controls
evidence: [810e8370a6841be6]
---
datasette-agent 0.3a0 adds an `execute_write_sql` tool that **asks the user for approval before writing** to a database and takes the user's existing permissions into account.

It is a small, concrete pattern worth copying: read tools run freely, write tools need a human yes, and the agent never holds more rights than the person driving it.
