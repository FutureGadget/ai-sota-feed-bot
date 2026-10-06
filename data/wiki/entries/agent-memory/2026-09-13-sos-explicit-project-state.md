---
title: "SOS serves an explicitly saved project state to new coding-agent sessions over MCP"
date: 2026-09-13
theme: recall-and-curation
evidence: [000d39be8c5e3832]
---
**SOS** stores a clearly defined "latest state" of a project inside the repository and serves it to a new or resumed session over [MCP](/topic/mcp). The author built it because Codex kept losing track of what was done, which decisions still held, and what needed re-verification.

State is explicitly saved, not inferred. **A superseded result stays in history but stops influencing the agent**, the same guarantee TEPA's revocation targets, applied to project status.
