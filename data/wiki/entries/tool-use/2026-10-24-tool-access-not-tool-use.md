---
title: "An agent that can quote the tool instruction still skips the tool: access is not invocation"
date: 2026-10-24
theme: calling-reliability
evidence: [b77efdf87fc0595e]
---
A developer exposed an `ask_user` MCP tool (speak a question, listen for the answer) to Claude Code. The agent used it in one project and printed the question on screen in the next, same machine, same day, even though it could quote the instruction back word for word.

This is a single practitioner report, not a controlled study. It shows that registering a tool and instructing its use does not guarantee invocation.

For builders: log tool-call rates per project or prompt context, and test that a tool is actually called, not just available.
