---
title: "NVIDIA preprint: 16K contexts with frequent compaction lose little accuracy"
date: 2026-11-04
theme: curating-the-working-set
evidence: [3c72c5c3cd7d0707]
also: [agent-cost]
---
An NVIDIA preprint ("You don't need long context") has frontier models summarize their own history to stay within a 16K window. It reports little accuracy loss for Claude Opus 4.5 and GPT 5.6 Sol, while long-context serving costs up to 7x more per token. The numbers are paper-reported, via a secondary news write-up.

For builders: budget for aggressive compaction before paying for a 1M-token window. Test your own workload first, since the study's tasks may not match yours.
