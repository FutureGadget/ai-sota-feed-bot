---
title: "Final-success scores hide non-executable tool-call trajectories; prefix executability scores the path"
date: 2026-10-30
theme: grading-trajectories
evidence: [bfc2f0eb7a62f683]
---
A new arXiv paper argues tool-use benchmarks that score only the terminal outcome can pass agents whose intermediate tool calls were not executable. It proposes **prefix executability**, a trajectory-level metric that checks how far into a call sequence the agent stays valid.

For builders, an agent can reach the right answer through calls that would fail or misfire against a stricter backend. Add a per-step validity check to your tool-use evals alongside pass rate, so regressions in call quality show up before they cost retries in production.
