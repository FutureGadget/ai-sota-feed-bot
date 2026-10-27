---
title: "Serving the RFC corpus through a skill or MCP server cuts reading tokens about 41x"
date: 2026-10-27
theme: discovery-and-definitions
evidence: [7b8f764b41e81a7e]
---
RFC AI Tooling exposes the IETF RFC corpus to agents two ways, as a skill and as an MCP server, both backed by the same stdlib-only Python core. Documents are fetched from the RFC Editor on demand, and obsoleted specs are flagged so agents stop citing dead ones. The author reports a median 41x saving (tokens approximated as bytes divided by 4; single-repo, self-measured).

Takeaway: a thin find-read-flag interface over a large reference corpus beats pasting documents into context. A skill and an MCP server can share one core instead of two implementations.
