---
title: "Flue's React-style hooks let an agent attach tools and subagents mid-run"
date: 2026-08-17
theme: loop-as-infrastructure
evidence: [8a940043da46a71f]
---
Astro creator Fred Schott's **Flue 2** borrows React's hooks: `useSkill()`, `useTool()`, `useSubagent()`, and custom hooks among 16 built-ins, so tools, resources, and state can attach or change **during a run** instead of being fixed in config up front.

His framing names the planning gap: a support or triage bot "can't be fully configured in advance... it has to adapt in real-time." The harness is the foundation, not an afterthought, which gives a concrete mechanism for re-planning mid-run.
