---
title: "Anthropic's tool search, programmatic calling, and input examples cut tokens and raise accuracy"
date: 2026-08-30
theme: discovery-and-definitions
evidence: [eafa6e2f9f229d66]
also: [mcp]
---
Three features on the Claude Developer Platform (vendor-reported numbers):

- **Tool Search Tool**: tools marked `defer_loading: true` are searched (regex or BM25) instead of loaded. A 50+ MCP-tool prompt drops from about 72K to about 500 tokens at rest (~3K per query); tool-heavy accuracy rises 49% to 74% on Opus 4 and 79.5% to 88.1% on Opus 4.5.
- **Programmatic Tool Calling**: Claude orchestrates tools in sandboxed Python, so intermediate results stay out of its context. Tokens fell 43,588 to 27,297 on a research task; GAIA rose 46.5% to 51.2%.
- **`input_examples`**: shows parameter conventions JSON Schema can't express; complex-parameter accuracy rose 72% to 90%.

On-demand discovery is a correctness fix, not only a context-budget one.
