---
title: "LongPIBench: simple injections beat leading defenses once context runs to tens of thousands of tokens"
date: 2026-09-02
theme: model-defenses
evidence: [2e8dd0bd140383d9]
---
LongPIBench tests prompt injection in four long-context scenarios (paper peer review, resume screening, code review, and email summary) with contexts of tens of thousands of tokens. **Even simple heuristic attacks bypass state-of-the-art defenses at high rates**, because nearly every published defense was measured on short inputs.

Agents routinely read long documents, repos, and inboxes. Treat short-context defense numbers as optimistic and test at the context lengths your agent actually sees.
