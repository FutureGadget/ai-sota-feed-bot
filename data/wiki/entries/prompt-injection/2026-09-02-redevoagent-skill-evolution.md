---
title: "RedEvoAgent distills successful attacks into reusable skills for automated red-teaming"
date: 2026-09-02
theme: model-defenses
evidence: [104986103cb850f2]
---
RedEvoAgent distills successful attack trajectories into short, reusable *skills* instead of replaying whole trajectories or using a fixed attack set. It credits which tool in an attack chain drove success (Deciding-Tool Attribution) and keeps only skill updates a validation pass confirms. The authors report it beats fixed and agentic red-teaming baselines and **transfers across attacker models and target harnesses**.

It targets agents in production execution harnesses, where a jailbreak triggers tool use and persistent state changes, not just unsafe text. A defense tested once will face stronger, self-improving attackers later.
