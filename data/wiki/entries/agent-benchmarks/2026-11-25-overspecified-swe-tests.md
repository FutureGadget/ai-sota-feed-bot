---
title: "Overspecified tests fail correct fixes in 23% of SWE-bench Verified and 35% of Pro tasks"
date: 2026-11-25
theme: trusting-the-score
evidence: [a4ca14fa7f75f3f5]
also: [agent-evaluation]
---
SWE-bench-style suites grade with tests from the original fix, which can enforce details the issue never states. The **Spec-Test Coverage Gap** scores overspecification 1-4 with two LLM judges given the spec and test patch; a task is flagged when both score 3+. On 206 audited tasks the judges caught **89%** of known overspecified tasks with a **4%** false-flag rate. Applied to whole suites, they flag **23%** of Verified and **35%** of public Pro. The authors loosened flagged requirements and regraded **2,186** failed patches from the top 30 Verified submissions.

For builders: some leaderboard failures are test artifacts. Before trusting a gap between agents, check whether the failing tasks demand unstated behavior.
