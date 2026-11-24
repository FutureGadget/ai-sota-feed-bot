---
title: "Most \"compatible\" MCP schema updates widen what an approved tool can do, and clients re-approve none of them"
date: 2026-11-24
theme: guarding-the-call
evidence: [388bf86f443549e4]
also: [mcp, version-pinning]
---
*SchemaCaps* surveyed 8 MCP clients and scanners and found none that re-approves a tool when its input schema widens. In a pilot over **604 releases of 39 public MCP servers**, **412 of 580** backward-compatible schema changes widened some argument, and at least **76** added or widened an authority-bearing one. The paper proposes a re-approval rule based on subschema inclusion, backed by a Coq proof and 48 regression tests; it asks for 645 re-approvals where pinning every change would ask 1,197.

For builders: approving a tool once approves its future versions too. Diff the input schema on every server update and re-prompt when an argument gains range or a new field appears.
