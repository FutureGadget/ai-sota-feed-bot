---
title: "StarHarness evolves the harness, tools included, for 20-35 point gains with frozen weights"
date: 2026-08-28
theme: calling-reliability
evidence: [3f6e2f7e73eca851]
---
**StarHarness** treats the whole harness as a search space while keeping model weights fixed: prompt and task framing, tool interfaces, skills, MCP-backed providers, subagent structure, and loop configuration. It stratifies tasks by how the default harness fails, separates proposal tasks from a hidden selection set, and holds out a third set to test generalization.

On ITBench SRE, EnterpriseOps-Gym ITSM, and AutomationBench Finance, the evolved harness beats the default by **20-35 percentage points** after 4-12 accepted changes, and gains transfer across GPT and Qwen without re-evolving.

Where OpenForgeRL trains the model to fit the harness, this tunes the harness and its tool surface instead.
