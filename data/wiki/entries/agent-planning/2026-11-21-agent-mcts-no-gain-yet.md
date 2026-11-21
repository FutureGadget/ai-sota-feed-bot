---
title: "Monte Carlo tree search over Claude Code does not yet beat a single first attempt"
date: 2026-11-21
theme: verify-and-replan
evidence: [ef67826b8d46f737]
also: [llm-as-judge]
---
agent-mcts (MIT, v0.3) wraps a coding-agent CLI in Monte Carlo tree search: it explores several solution branches, backtracks from dead ends, and spends more budget on the promising path. On two harder tasks scored by hidden tests (Claude Code with Haiku, 5-episode budget, 10 runs per setting), the author reports **no gain over the run's own first attempt** yet. An earlier 99% vs 90% result came from easy tasks where first attempts already scored 98% or more.

The author names the branch judge as the bottleneck. For builders: test-time search only pays when the selector beats chance on hard cases, so measure the judge before adding branches.
