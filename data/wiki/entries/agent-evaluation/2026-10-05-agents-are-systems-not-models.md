---
title: "Run-to-run repetition explains ~54% of agent outcome variance"
date: 2026-10-05
theme: score-validity
evidence: [068e3817b6d56fbd]
---
"Agents Are Systems, Not Models" varies five configuration settings — task information, reasoning, self-verification, time budget, backbone model — on four scientific tasks where a coding agent must find and operate a published specialist model.

- About **54% of outcome variance** came from repeating the same configuration, so single-run comparisons are noisy.
- Task information had the largest effect, more than time budget or model size; extra time helped only with enough information or capability.
- Prompting the agent to verify barely changed behavior; a **dedicated verification tool** did.

Evaluate the configuration, with repeated runs per setting.
