---
title: "AWS market-surveillance reference pairs LangGraph control flow with Strands agents on AgentCore"
date: 2026-07-28
theme: production-evidence
evidence: [f5869c6c9f8fd679]
also: [agent-orchestration]
---
An AWS reference architecture for capital-markets surveillance uses **LangGraph for workflow orchestration and Strands for agent reasoning** on Amazon Bedrock AgentCore, with state-driven orchestration, **checkpoint-based recovery**, and AgentCore's built-in memory and observability.

Two frameworks split the job: one owns the deterministic graph and recovery, the other the agent reasoning. Recovery and memory come from the platform instead of being hand-rolled.
