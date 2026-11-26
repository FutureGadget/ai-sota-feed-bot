---
title: "Drums forks isolated Linux desktops from CRIU checkpoints in 139 ms, packing hundreds per host"
date: 2026-11-26
theme: fleet-density
evidence: [415f33463dc26d9a]
also: [agent-sandboxing]
---
Computer-use agent training needs thousands of isolated desktops, usually one VM each with its own kernel and boot. Drums, an open-source host daemon, runs hundreds of isolated Linux desktops on one server instead. It restores them from CRIU checkpoints and forks or resets them without a reboot, in **139 ms** per the project. Every episode also gets a gate report and a reward audit.

For builders: checkpoint-and-fork moves desktop environments from per-VM boot cost to process-restore cost. That changes how many parallel RL or eval rollouts one machine can hold. The density and isolation claims are project-reported; check the isolation boundary before running untrusted agents this way.
