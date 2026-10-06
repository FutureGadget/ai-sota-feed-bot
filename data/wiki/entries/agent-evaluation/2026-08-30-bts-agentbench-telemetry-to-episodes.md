---
title: "BTS-AgentBench compiles read-only telemetry logs into replayable agent benchmarks"
date: 2026-08-30
theme: domain-benchmarks
evidence: [ae8e4d039d14f79b]
---
**BTS-AgentBench** turns read-only industrial telemetry into executable multi-turn agent episodes through a deterministic pipeline: normalize metadata, build a read-only tool store, compile tasks with gold answers and evidence, bind them into typed episodes. Quality gates include contract preflight reports, timestamp policies, and evidence attribution; independent rebuilds matched all **11 tool-store exports**.

Applied to one system (XAI4HEAT) it produced **204 episodes**. It is a recipe for building benchmarks from your own production logs.
