---
title: "LinkedIn splits AI code review across specialized agents to keep up with PR volume"
date: 2026-08-23
theme: production-evidence
evidence: [1ed24debfc2b958d]
---
At LinkedIn's scale, neither human reviewers alone nor an **off-the-shelf AI reviewer in front of GitHub** kept up with PRs. Engineers built a multi-agent code review platform that understands the organization's coding context, treats review as production infrastructure, and aims to minimize hallucinations and low-signal comments.

The reviewer role is split across specialized agents instead of asking one model to catch every class of issue in one pass.
