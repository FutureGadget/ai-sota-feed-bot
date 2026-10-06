---
title: "KC-Bench: no model reliably reconciles user, parametric, and tool knowledge conflicts"
date: 2026-09-06
theme: long-horizon-and-subsystems
evidence: [71d13489a25b073e]
---
**KC-Bench** isolates how agents reconcile conflicts between user instructions, parametric knowledge, and tool observations. Its 238 multi-turn tasks, screened from over 1,000 candidates, combine a user simulator, stateful tools, deterministic assertions, and human trajectory verification.

Across nine models, including DeepSeek-V4-Flash, GLM-5.2, and MiniMax-M3, **none reliably handles** factual correction, identity consistency, and temporal conflicts in every setting. A missed conflict can propagate straight into a tool call.
