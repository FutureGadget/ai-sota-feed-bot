# Agent Engineering Wiki — catalog

Human-readable catalog of the wiki. The machine-readable served artifact is
`index.json` (compiled by `pipeline/build_wiki.py`; do not hand-edit). Pages
live under `obstacles/` and `solutions/`. Schema: `config/wiki_schema.md`.

## Obstacles by area

### evaluation
- [agent-evaluation](obstacles/agent-evaluation.md) — Measuring whether an agent actually worked is hard
  → solutions: llm-as-judge, agent-benchmarks

### memory
- [agent-memory](obstacles/agent-memory.md) — Agents forget across steps and sessions
  → solutions: vector-kb, context-compaction

### multi-agent
- [multi-agent](obstacles/multi-agent.md) — Coordinating multiple agents adds more failure than capability
  → solutions: agent-orchestration, agent-benchmarks

### security
- [prompt-injection](obstacles/prompt-injection.md) — Untrusted input and tools can hijack an agent
  → solutions: agent-sandboxing

### tool-use
- [tool-use](obstacles/tool-use.md) — Agents reach the outside world through fragile, ad-hoc integrations
  → solutions: mcp

## Solutions
- [agent-benchmarks](solutions/agent-benchmarks.md) — Fixed tasks that exercise real tool use
- [agent-orchestration](solutions/agent-orchestration.md) — Orchestration patterns: topologies, handoffs, and harnesses
- [agent-sandboxing](solutions/agent-sandboxing.md) — Sandboxing, scoped credentials, and guardrails
- [context-compaction](solutions/context-compaction.md) — Summarize, compress, and curate the working set
- [llm-as-judge](solutions/llm-as-judge.md) — Model-graded evaluation of traces and outputs
- [mcp](solutions/mcp.md) — Model Context Protocol: a standard interface for agent tools
- [vector-kb](solutions/vector-kb.md) — External knowledge base: vector and graph retrieval
