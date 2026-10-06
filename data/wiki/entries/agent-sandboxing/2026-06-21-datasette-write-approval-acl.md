---
title: "datasette-agent gates database writes behind user approval on top of resource-level ACLs"
date: 2026-06-21
theme: permission-policy
evidence: [810e8370a6841be6, 68a519e26dde7563]
---
datasette-agent 0.3a0 adds **`execute_write_sql`**, which asks the user for approval and then writes while respecting that user's permissions. An `--unsafe` mode auto-approves. Two days later datasette-acl 0.6a0 grew from table-only permissions toward a **general resource-sharing system** for multi-user instances.

The pattern: reads flow freely, writes need a human yes, and both are bounded by the caller's own ACLs rather than the agent's.
