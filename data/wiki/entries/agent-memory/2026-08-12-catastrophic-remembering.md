---
title: "CLAUDE.md keeps growing because deleting an instruction is costlier than adding one"
date: 2026-08-12
theme: recall-and-curation
evidence: [ffff9fe41413e4ac]
---
Across **247,694 instruction lifetimes**, agentic-coding files like `CLAUDE.md` grow without bound until the repo retires or someone rewrites the file. Appending is cheap; once an instruction's rationale is gone, deleting it safely costs O(2^|D|) for |D| instructions. The paper calls this **catastrophic remembering**, the inverse of catastrophic forgetting.

This store has no retrieval step: the whole file loads every turn. The fix is write-time deduplication and pruning, not better recall.
