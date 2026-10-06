---
title: "GitHub: truncating agent output to save tokens can raise total task cost"
date: 2026-09-05
theme: harness-and-context
evidence: [fbfd060b861c9942]
---
GitHub found that when a coding agent's output was truncated or summarized to save tokens, the agent sometimes **reopened the original or reran the command**, turning one cheaper turn into more turns and more context. Its fixes, measured across the whole task:

- Selectively compress repetitive build/test logs while keeping source code (the largest cut)
- Strip unused line-number formatting (**5%**)
- Less verbose Task-tool prompts (**2.9%**)
- Deliver background results without an extra retrieval call (**2.3%**)

Each change passed offline benchmarks and online A/B tests. Measure cost per task, not per tool call.
