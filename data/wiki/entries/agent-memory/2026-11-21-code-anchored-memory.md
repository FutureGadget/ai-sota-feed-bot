---
title: "Coding-agent memory goes stale as code moves; anchoring notes to symbols keeps it verifiable"
date: 2026-11-21
theme: recall-and-curation
evidence: [3aa4c25fca280121]
---
Enola studied how coding agents reuse saved investigations across sessions. Three failures recur: a line reference drifts to unrelated code after edits elsewhere in the file, a later agent never retrieves the note because it uses different terminology, or it retrieves notes about an unrelated function that shares a name.

Its approach ties each memory to **source-code structure through symbol tracking**, so a retrieved note can be checked against the current version of the function before the agent trusts it. For builders: Markdown notes and session summaries need a code reference, or old conclusions get applied to code that has since changed.
