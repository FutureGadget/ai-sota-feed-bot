---
title: "Kog Laneformer 2B is a latency-first small model built with its inference engine"
date: 2026-06-30
theme: less-work-per-step
evidence: [537f21de13e2a85a]
---
Kog built Laneformer 2B as a **latency-first model**, designed together with the Kog inference engine rather than adapted to a fast server after the fact.

Most of an agent's calls don't need frontier breadth. Sending the bulk of them to a small, predictable model is the same downshift that controls [cost](/topic/agent-cost), applied to wall-clock time.
