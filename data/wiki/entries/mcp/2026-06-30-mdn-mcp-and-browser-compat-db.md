---
title: "Mozilla's MDN MCP service puts reference data behind the protocol"
date: 2026-06-30
theme: beyond-tools
evidence: [802363aee5105ca5]
---
Mozilla launched an **MDN MCP service**. Inspired by it, Simon Willison converted the mdn/browser-compat-data repository into a ~66MB SQLite database (`simonw/browser-compat-db`) so the data can be queried directly.

MCP carries reference knowledge, not only actions, and community spinoffs repackage the same data in queryable form.
