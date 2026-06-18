# Agent Engineering Wiki — catalog

Human-readable catalog of the wiki. The machine-readable served artifact is
`index.json` (compiled by `pipeline/build_wiki.py`; do not hand-edit). Pages
live under `obstacles/` and `solutions/`. Schema: `config/wiki_schema.md`.

## Obstacles by area

### memory
- [agent-memory](obstacles/agent-memory.md) — Agents forget across steps and sessions
  → solutions: vector-kb, context-compaction

## Solutions
- [vector-kb](solutions/vector-kb.md) — External knowledge base: vector and graph retrieval
- [context-compaction](solutions/context-compaction.md) — Summarize, compress, and curate the working set
