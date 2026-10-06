---
title: "Six SDK releases in a week; one carried a real permission-behavior fix"
date: 2026-07-16
theme: bundled-cli-bumps
evidence: [2832f2f825db2411, cac4c9ead20e55a3, f0c081fcc40a7583, ea8bf0e5641cf4c4, 2eb4a06e737c3d47, f038f32830795715]
---
The Claude Agent SDK rolled from v0.2.115 to v0.2.120 in about a week, advancing the bundled CLI from 2.1.206 to 2.1.211. Most entries say only "Updated bundled Claude CLI".

**v0.2.116 was not cosmetic**: it fixed CI workspace trust so Claude Code honors project-scoped permission grants in checkout directories. v0.2.117 also escaped untrusted fields in the repo's Slack notification workflow.

A permission-behavior change arrived looking like one more version bump. Keyword-skimming the SDK changelog would miss it.
