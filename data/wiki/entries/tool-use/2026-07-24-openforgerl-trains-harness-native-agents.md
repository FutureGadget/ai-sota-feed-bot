---
title: "OpenForgeRL records harness model calls as RL data to train harness-native agents"
date: 2026-07-24
theme: calling-reliability
evidence: [7a982846f4848d96]
---
Harnesses such as Claude Code, Codex, and OpenClaw are stateful, multi-process systems that open SFT/RL stacks cannot express, so training a harness-native agent end to end was out of reach. **OpenForgeRL** puts a lightweight proxy in front of the harness's model calls and records them as RL training data (for example, for veRL), with a Kubernetes orchestrator running each rollout in its own remote container.

It is validated on tool/harness agents and on GUI and browser-use agents, beating open baselines of similar size on nearly every benchmark tested (ClawEval, QwenClawBench, OSWorld-Verified, Online-Mind2Web, WebVoyager).
