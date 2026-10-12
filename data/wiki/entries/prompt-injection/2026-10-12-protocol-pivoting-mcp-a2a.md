---
title: "Protocol pivoting: injected text hops between agents because each one trusts its peer"
date: 2026-10-12
theme: agent-authorization
evidence: [38a23f681b4cd66d]
also: [mcp, multi-agent]
---
An independent researcher showed prompt injection that targets a *peer agent* rather than the model: text planted in content reaches one agent over MCP, which forwards it as a normal delegated task over another protocol such as A2A. The receiving agent runs it because it trusts the sender, and MCP servers hold each agent's credentials. Agents from Google, Rapid7, and three other organizations were affected, per press reporting. Google's flaw (CVSS 8) was a database MCP server following redirects with no IP validation, an SSRF.

Another researcher calls it plain indirect injection. For builders: treat anything an LLM or peer agent hands your tool as untrusted input, and require authorization per hop.
