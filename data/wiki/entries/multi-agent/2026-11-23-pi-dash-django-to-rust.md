---
title: "26 agents ported a 101K-line Django backend to Rust in ten days for about $350, per the vendor"
date: 2026-11-23
theme: production-evidence
evidence: [ea0942d08cef728f]
also: [agent-orchestration]
---
AI Republic's Pi Dash coordinated 26 coding agents on five machines through a written rulebook issue, a coordinator agent that never wrote code, and separate fresh-context runs for implement, review, test, and merge. The vendor reports about **1,320** merged PRs, **48.6B** tokens costing about **$350**, and 5,029 contract tests run against both backends.

Humans still mattered: they freed sandbox disk by hand, relaxed the byte-exact JSON rule mid-project, and pace fell while agents waited for people to check results. For builders: contract tests against the old system gave the agents a checkable "done", and splitting review from implementation stopped self-approval.
