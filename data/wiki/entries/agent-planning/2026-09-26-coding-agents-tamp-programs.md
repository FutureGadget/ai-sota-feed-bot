---
title: "Coding agents write task-and-motion planners that beat hand-engineered ones (56-95% vs. 47%)"
date: 2026-09-26
theme: learned-planning
evidence: [44bb531f443ceb51]
---
Claude Code (Opus 5) and Codex (GPT-5.6 Sol, GPT-6 Astra) were each given a task description, simulator access, and a fixed budget to **synthesize a reusable planning program**, which was then frozen and tested on unseen instances. Across 28 environments (980 programs, 98,000 episodes), all three beat hand-engineered planners: **56-95% mean success versus 47%** on the 16 environments with a planner baseline.

As object counts grew, the agents' programs kept their edge with an order of magnitude less computation per instance. Letting an agent write the plan as code generalizes better and cheaper than re-planning each episode.
