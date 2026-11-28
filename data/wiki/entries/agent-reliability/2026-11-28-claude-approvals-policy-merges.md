---
title: "Claude Ship lets a repo policy file decide when Claude's review counts as a merge approval"
date: 2026-11-28
theme: verifying-the-work
evidence: [6b49f53898430814]
also: [agent-sandboxing]
---
Anthropic's Claude Ship bundles Code Review (GA), PR Steward (beta), which fixes CI, conflicts, and review feedback but never approves or merges, and Claude Approvals (beta). Approvals reads `.claude/approvals.yml` from the default branch. Per path pattern, it sets how many human seats a change needs and whether Claude approves, comments, or blocks.

Approval is the risky part. The author can fill a seat, so `seats: 0` can merge a bot-authored PR with no person involved. Claude's approval can also satisfy GitHub's one-approval rule. A PR that edits the policy is judged by the rules already merged.

For builders: start in `mode: observe`, require humans on the policy file, and pin merges to the reviewed head SHA so a background push can't land unreviewed.
