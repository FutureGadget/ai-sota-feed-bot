---
title: "iFood turns repo chores across 15,000 repositories into API calls that return merge requests"
date: 2026-11-25
theme: orchestrator-tooling
evidence: [89a905d5eae9fa3e, 8655fa232145e922]
also: [proving-agent-roi]
---
iFood's **Remote Agents Platform** handles recurring per-repo work (standards validation, vulnerable-dependency fixes, analyses) across more than **15,000** repositories. A team delegates a task by API; a coding agent runs in a remote sandbox; the result comes back as a merge request for human review. The company says its internal security platform more than **doubled** vulnerabilities fixed after adoption (customer story published by OpenAI).

For builders: fleet-wide chores are easy one at a time and expensive at scale. A task API with sandboxed execution and merge-request output gives one integration point to govern, review, and meter.
