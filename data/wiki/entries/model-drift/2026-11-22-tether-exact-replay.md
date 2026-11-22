---
title: "A trace that holds all run state makes exact replay a free regression suite for policy and prompt changes"
date: 2026-11-22
theme: drift-tooling
evidence: [bd45098603528b17]
also: [agent-tracing, agent-evaluation]
---
Tether, a Rust harness that wraps any agent, writes one append-only JSONL trace and keeps **no state that is not also an event in it**. Model responses, tool results, human answers, and the clock are recorded at the boundary, so a replay reproduces the run field for field with no network or spend.

Policy is the one part re-evaluated on replay, so a week of production traces becomes a free test suite for a stricter rule set. A changed prompt or model replays up to the first differing request, then goes live; `diff` names that request. Resume, eval, and OpenTelemetry export are all readers of the same file. For builders: record every nondeterministic input, and replay becomes your drift test.
