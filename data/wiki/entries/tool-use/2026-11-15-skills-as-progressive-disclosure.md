---
title: "Skill descriptions should say when to load the skill, because too many descriptions degrade selection"
date: 2026-11-15
theme: discovery-and-definitions
evidence: [3064a8ace1fdfaeb]
also: [context-compaction]
---
PostHog runs **226** internal skills and **187** `SKILL.md` files across 28 products. Its lesson: a skill is a router for progressive disclosure. Only the name and description stay in context, so they should state *when* to reach for the skill, not what it is.

Too many skills, or long descriptions, hurt. PostHog saw agent effectiveness drop as descriptions filled its PostHog AI context, and cites Databricks finding wrong-skill picks rising with skill count. Its SQL skill is a thin workflow that links out to 26 schema files and 22 query patterns.

Over-specified steps ("read lines 40-120 of auth.py") break when the repo changes; goal-level guidance survives. For builders: budget the always-loaded description text like a tool catalog.
