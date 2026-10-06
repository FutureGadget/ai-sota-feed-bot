---
title: "Azure DevOps Remote MCP Server reaches GA, but Claude, ChatGPT, and Cursor can't connect"
date: 2026-08-22
theme: servers-in-production
evidence: [857f4a269c2fa11e]
also: [tool-use]
---
Microsoft made the **Azure DevOps Remote MCP Server** generally available: a hosted endpoint into work items, repos, and pipelines with nothing to install. Claude Desktop, Claude Code, ChatGPT, and Cursor cannot connect yet, because Entra lacks dynamic client registration and Client ID Metadata Documents.

"GA" and "works with every major MCP client" are still separate milestones, and the gap sits in the auth layer.
