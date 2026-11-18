---
title: "LangSmith lets engineers debug traces without seeing the sensitive inputs and outputs inside them"
date: 2026-11-18
theme: storage
evidence: [a373cca9a4fe103c]
---
LangSmith added three access controls for production traces. Admins can hide **inputs and outputs** (user messages and model responses) while engineers still see run trees, latency and cost. Workspace and data access can be set per **user group**. Trace-level policies read **root-run metadata**, so access to one customer's traces can be granted only to the people handling that customer's issue.

This targets the usual workaround of duplicate traces and separate workspaces, or not sending traces at all, for data under GDPR, HIPAA or SOC 2 obligations. For platform teams, least-privilege access in the trace store is becoming a standard requirement for observability vendors.
