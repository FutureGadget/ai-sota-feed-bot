---
title: "AWS splits production agent monitoring into quality scoring and infrastructure investigation"
date: 2026-09-16
theme: eval-in-production
evidence: [381ed851c46a02e9]
---
AWS pairs **Amazon Bedrock AgentCore Evaluations** (continuous quality scoring) with **AWS DevOps Agent** (autonomous infrastructure investigation) to monitor a production multi-agent system, shown on a four-agent airline reservation system.

The premise: multi-agent failures slip past traditional monitoring, so quality scoring has to run continuously on live traffic beside infrastructure checks.
