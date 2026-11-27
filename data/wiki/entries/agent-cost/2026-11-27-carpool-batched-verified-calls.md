---
title: "Carpool batches independent tasks into one verified request, cutting cost per accepted answer ~80%"
date: 2026-11-27
theme: harness-and-context
evidence: [f2a29141f92b3b28]
also: [cost-controls]
---
Every separate model call pays its fixed setup again: system prompt, tool schemas, instructions. Carpool sends independent tasks in one request. Each answer must cite a source ID, and rule-based checks (exact text, numbers with units, names) verify it with no extra model call. Only tasks that fail a check get their own full-evidence retry. On 24 ops tasks and 48 SQuAD questions with Claude, cost per accepted answer fell **78-83%** against one lean call per task and **93-96%** against one agent call per task, with zero regressions. The authors note the small sample bounds regressions only at about 6%.

For builders: per-item agent calls in a pipeline mostly buy repeated setup. Batch them, and verify each answer mechanically instead of with another model.
