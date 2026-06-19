# Wiki activity log

Append-only, newest last. One line per ingest/lint action by `wiki-curator`.
Format: `YYYY-MM-DD  <op>  <slug…>  — <note>`.

2026-06-18  seed  agent-memory vector-kb context-compaction  — initial memory cluster seeded by hand to prove the build→render→serve loop
2026-06-19  ingest  agent-evaluation llm-as-judge agent-benchmarks tool-use mcp prompt-injection agent-sandboxing  — folded last-7d clusters into three new obstacle areas (evaluation, tool-use, security) + four solutions: trajectory/trace eval (Strands, 100x trace judge, deployment simulation, out-of-distribution gauntlet); MCP as the tool-interop standard (Terraform GA, WebMCP in Chrome, enterprise managed auth); injection defense as least-privilege (sandbox ≠ credential auth, guardrail-as-DoS, Deep-XPIA)
2026-06-19  ingest  multi-agent agent-orchestration  — new multi-agent obstacle area + agent-orchestration solution: topology (not agent count) dominates coordination cost/quality (DPBench), decentralizing away from a central orchestrator cuts task cost ~50% (Stanford DeLM), per-task generated execution harnesses (Anthropic Dynamic Workflows); cross-linked multi-agent→agent-benchmarks (DPBench measures coordination)
