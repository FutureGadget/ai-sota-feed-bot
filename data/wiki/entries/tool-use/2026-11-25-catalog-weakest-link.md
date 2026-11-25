---
title: "Per-attack blocking hides catalog risk: 92% blocked, yet 99% of 200-tool catalogs leak"
date: 2026-11-25
theme: guarding-the-call
evidence: [db68a7b8e354aade]
also: [prompt-injection]
---
Runtime controls such as ChainCaps rely on per-tool manifests stating what each tool may read and where output may go. Evaluations report **per-attack blocking**, but a catalog is only as safe as its weakest manifest: with *M* policies each wrong with probability *p*, exposure is `1-(1-p)^M`. In synthetic catalogs, blocking held at **92%** while catalog vulnerability rose from **22% at 10 tools to 99% at 200**. On **114 real MCP tools**, model-written manifests blocked 89% of attacks yet left **9 of 15** catalogs open. Errors cluster by author, so a 200-tool catalog acts like about 5 independent decisions.

For builders: report catalog-level exposure and sink coverage, and review manifests per author, not per tool.
