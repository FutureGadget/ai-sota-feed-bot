---
title: "JSON-schema output constraints suppress tool calling in open-weight models"
date: 2026-06-26
theme: calling-reliability
evidence: [d0a3b1456466205e]
---
The "Constraint Tax" study reports a reproducible effect first seen in a production agent: with **tool calling and JSON-schema constraints enabled together**, several open-weight models stop invoking tools while still producing valid structured output.

The two core agent capabilities interfere. Forcing a clean output contract can quietly stop the agent from calling the tool it needed, so test the combination you deploy, not each feature alone.
