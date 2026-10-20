---
title: "Agents that query for skills mid-task beat static retrieval, but under-invoke and add latency"
date: 2026-10-19
theme: discovery-and-definitions
evidence: [100331f97937a9e5]
---
SkillBrowser targets **Selective Skill Exposure**: loading procedural skill content only when needed. Progressive disclosure lists metadata for the whole library and pollutes context. Static retrieval from the initial task query misses needs that emerge mid-reasoning.

A meta-skill has the agent name its current capability need, issue a targeted query, and load matching skills on demand. Across six SRA-Bench subsets and five LLMs (paper-reported), it improves aggregate accuracy over static retrieval and LLM-based selection, and limits accuracy loss on instances the model already solves.

The authors report model- and task-dependent gains, under-invocation of useful skills, and added latency. Large skill libraries need a retrieval step the agent controls, not a catalog dumped into the prompt.
