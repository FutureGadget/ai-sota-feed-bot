# Agent Engineering Wiki — catalog

Human-readable catalog of the wiki. The machine-readable served artifact is
`index.json` (compiled by `pipeline/build_wiki.py`; do not hand-edit). Pages
live under `obstacles/` and `solutions/`. Schema: `config/wiki_schema.md`.

## Obstacles by area

### cost
- [agent-cost](obstacles/agent-cost.md) — Agent token costs are unpredictable and easily run away
  → solutions: cost-controls, context-compaction, agent-orchestration
- [proving-agent-roi](obstacles/proving-agent-roi.md) — Proving agent ROI and measuring cost efficiency is hard
  → solutions: cost-controls, llm-as-judge

### evaluation
- [agent-evaluation](obstacles/agent-evaluation.md) — Measuring whether an agent actually worked is hard
  → solutions: llm-as-judge, agent-benchmarks

### drift
- [model-drift](obstacles/model-drift.md) — Agent behavior drifts as the model, SDK, and runtime churn under it
  → solutions: version-pinning, agent-benchmarks

### latency
- [agent-latency](obstacles/agent-latency.md) — Agent loops multiply per-call latency into slow, expensive runs
  → solutions: speculative-decoding, context-compaction

### memory
- [agent-memory](obstacles/agent-memory.md) — Agents forget across steps and sessions
  → solutions: vector-kb, context-compaction

### multi-agent
- [multi-agent](obstacles/multi-agent.md) — Coordinating multiple agents adds more failure than capability
  → solutions: agent-orchestration, agent-benchmarks

### observability
- [agent-observability](obstacles/agent-observability.md) — You can't see why an agent did what it did
  → solutions: agent-tracing

### planning
- [agent-planning](obstacles/agent-planning.md) — Agents plan multi-step work badly — they loop, stall, or skip steps
  → solutions: agent-orchestration

### reliability
- [agent-reliability](obstacles/agent-reliability.md) — Agents give fluent, confident-looking output even when it's wrong
  → solutions: agent-sandboxing

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
- [agent-tracing](solutions/agent-tracing.md) — Tracing and trace analysis for agent runs
- [context-compaction](solutions/context-compaction.md) — Summarize, compress, and curate the working set
- [cost-controls](solutions/cost-controls.md) — Budgets, metering, and per-task cost attribution
- [llm-as-judge](solutions/llm-as-judge.md) — Model-graded evaluation of traces and outputs
- [mcp](solutions/mcp.md) — Model Context Protocol: a standard interface for agent tools
- [speculative-decoding](solutions/speculative-decoding.md) — Draft cheaply, verify in parallel to cut decode latency
- [vector-kb](solutions/vector-kb.md) — External knowledge base: vector and graph retrieval
- [version-pinning](solutions/version-pinning.md) — Version pinning, compatibility ranges, and staged upgrades
