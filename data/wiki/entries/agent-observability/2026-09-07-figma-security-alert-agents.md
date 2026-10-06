---
title: "Figma's security agents resolve complex alerts 70% faster, with memory as the main lever"
date: 2026-09-07
theme: agentic-rca
evidence: [ac7780096954b97a]
---
Figma built alert-triage agents on a Panther SIEM foundation, querying 100+ data sources (AWS, Okta, GitHub, GCP, osquery) and scoped to the tools an on-call engineer uses. The team reports **memory, not model choice or tool count**, as the biggest quality lever.

Reported results: **70% faster resolution** on complex alerts, 20% fewer on-call pages from re-tuned severity, and 100+ previously unknown vulnerabilities found. Agent-authored PRs default to draft and every fix needs human approval.
