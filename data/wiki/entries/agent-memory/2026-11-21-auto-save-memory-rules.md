---
title: "Auto-saved memory stored one-off requests as rules until plain filters and inline Undo were added"
date: 2026-11-21
theme: memory-integrity
evidence: [e1150fe2f9e639ca]
---
NEXUPIRA first queued every extracted memory for owner approval on a settings page. Small-business users never opened it, so the assistant remembered almost nothing. Switching to automatic saves, two days of production testing showed it storing **a one-off request as a standing rule**, a test question as a business plan, and its own option list as a fact about the owner.

The fixes were mostly **regular expressions and a word-overlap count**, plus showing each save under the answer with an **Undo button**. For builders: approval queues that live off the main path don't get used; put consent inline and filter the write path deterministically.
