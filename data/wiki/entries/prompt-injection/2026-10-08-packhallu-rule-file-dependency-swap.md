---
title: "Injected rule files can steer coding agents to swap in attacker-controlled packages"
date: 2026-10-08
theme: injection-paths
evidence: [7846186c47bfadc6]
---
A new paper defines the **package hallucination attack**: an attacker injects prompts into otherwise benign community rule files (`AGENTS.md`, `.cursorrules`) so a coding agent replaces legitimate dependencies with attacker-controlled packages. Its PackHallu framework evolves the injected prompt using trajectory-level feedback and LLM-guided mutations. The authors report high attack success and strong transfer across models and agent frameworks; the abstract gives no figures.

For builders: treat shared rule files as untrusted input, review dependency diffs an agent produces, and pin or allowlist package sources.
