---
title: "CivBench catches agents skipping state checks they planned across 300+ turns of Civilization VI"
date: 2026-09-06
theme: long-horizon-and-subsystems
evidence: [96e818e4eab0da8b]
---
**CivBench** runs 300+-turn episodes across 76 [MCP](/topic/mcp) tools in Civilization VI, grading sustained planning and state monitoring under partial observability. Its pilot (23 runs, four model families) says aggregate scores don't yet discriminate models.

Two interface-level metrics did catch failures: **Proactive Monitoring Rate** and **RAG@10** (whether a commitment in the agent's own plan executes within ten turns). Agents told to check victory progress every 20 turns did so only every 30-75, and missed the check before 7 of 20 detectable defeats.
