---
slug: mcp-security-control-layers
title: "What actually breaks when you run MCP in production, and how do you defend it?"
question: "What actually breaks when you run MCP in production, and how do you defend it?"
summary: "Documented MCP CVEs cluster in four layers: unsafe tool execution, unauthenticated management endpoints, unrestricted outbound calls, and undetected tool-definition drift. A gateway defends none of them directly; each needs its own control, enforced closer to the failure."
status: active
cluster: safety
updated: 2026-11-06
audience: "strong-software-engineer"
related_topics: [mcp, agent-sandboxing, prompt-injection]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: infoq-mcp-defense-in-depth
    kind: production-field-report
    title: "Securing MCP in Production: Defense-in-Depth Beyond the Gateway"
    url: "https://www.infoq.com/articles/securing-mcp-production-gateway/"
    added: 2026-08-08
    note: "Groups 30 documented MCP CVEs into four layers: 13 from unsafe execution (shell interpolation, exec/eval on input), six from unauthenticated inspector, test-harness, or registration endpoints, outbound trust (CVE-2026-26118, an Azure SSRF leaking a managed-identity token), and post-registration definition drift ('rug-pull'). Recommends argument arrays, authenticated and isolated management endpoints, egress allow-lists with per-purpose credentials, and SHA-256 manifest pinning with operator review."
  - id: copex-2026-mcp-adversarial-context
    kind: benchmark-result
    title: "COPEX: Benchmarking LLM Robustness to Adversarial Context Across Model Context Protocol Layers"
    url: "http://arxiv.org/abs/2610.04378v1"
    sid: "b0a6adb95dddda44"
    added: 2026-10-07
    note: "Holds the agent stack fixed and varies only the tool-selecting model: 25 attack types, 125 scenarios, four entry surfaces (model/agent, client, server/tool, transport), nine models, 3,375 trials. Mean attack success is 64.4%, 58.3% to 71.4% by surface. Some client and transport attacks succeed outside the model's view. Combined input and context scanning cut mean success 49.6% on an eight-attack subset."
  - id: mcpvenom-2026-tool-poisoning-measurement
    kind: benchmark-result
    title: "MCP Tool Poisoning in Agentic AI Frameworks: A Cross-Framework Measurement Study"
    url: "http://arxiv.org/abs/2611.03555v1"
    sid: "f4762eccd1c3e217"
    added: 2026-11-06
    note: "Runs real tool execution across 12 frameworks, 18 models, 45 scenarios (9,720 cells). Overall attack success is 22.9%; of successes, 12.1% verifiably exfiltrate a secret. Resistance is model-level: nine frameworks cluster at 23-26% and none implements intentional defense. A regex description scanner rejects 20 of 45 scenarios at a 7.2% false-positive rate."
  - id: etude-2026-tool-update-gap
    kind: benchmark-result
    title: "Beyond Prompt Injection: The Tool Update Gap in LLM Agent Security"
    url: "http://arxiv.org/abs/2611.01976v1"
    sid: "3b426192f1bc75ae"
    added: 2026-11-06
    note: "ETUDE embeds malicious code in an update to an initially benign tool. Across seven frameworks including Gemini CLI, Codex CLI, and Claude Code it reaches 97.6% attack success with 95.9% legitimate task completion. The payload runs outside the model's context, so in-context defenses do not see it."
  - id: germline-2026-signed-tool-leak
    kind: benchmark-result
    title: "Signed, Sealed, Leaked: Trust Beyond Signature for MCP Toolchains"
    url: "http://arxiv.org/abs/2611.06585v1"
    sid: "1c990a2a55a59e80"
    added: 2026-11-06
    note: "A validly signed MCP tool leaks data to a policy-allowed destination and defeats Meta's MCPGuard-Dynamic in every trial. Germline execution forks each call from a data-free process holding only destination-authorised data: no disclosure in 153 attack runs versus 5.9-74.5% under baselines."
  - id: aws-agentcore-mcp-2026-07-28-spec
    kind: story
    sid: b734d716b0d66f96
    title: "How AgentCore Gateway supports the MCP 2026-07-28 spec"
    added: 2026-08-08
    note: "Context: the hardening guidance landed one day after MCP's 2026-07-28 spec revision, which changed authorization but left execution, management, outbound, and integrity risks to deployment-level controls."
  - id: mcp-security-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-08-08
    note: "A routing gateway sits at the network edge, while three of the four failure classes (unsafe execution, outbound exfiltration, definition drift) originate inside or behind the MCP server. A gateway enforces inbound auth and rate limits but cannot see what a tool does once a call reaches it."
---

## Builder consequence
If "securing MCP" means "put it behind an authenticated gateway," you have covered one layer of four. Documented MCP CVEs mostly happen inside or behind the server the gateway fronts: how a tool executes arguments, what the server can reach outbound, and whether a tool's definition or code still matches what was approved. A gateway's inbound auth check inspects none of these, and a valid signature does not prove the tool is benign.

## Short answer
MCP vulnerabilities cluster into four layers, each stopped at a different point:

- **Execution** — arguments reach a shell or `eval()`.
- **Management** — inspectors, test harnesses, and registration endpoints left unauthenticated.
- **Outbound trust** — a server can call any URL with a privileged credential.
- **Semantic integrity** — a tool's definition changes after approval.

A gateway is an inbound routing and auth control. Three of the four failures happen behind it.

## Builder model
Model each MCP server as a small privileged service with its own attack surface, not a trusted host inside a gateway perimeter. Ask four questions:

1. Does it turn caller arguments into a shell command or evaluated code?
2. Are its non-agent interfaces (debug, CI, registration) authenticated?
3. What can it reach outbound, and with which credential?
4. Can its advertised behavior change without anyone noticing?

A gateway answers "who may call this server," a real but separate question.

## Mechanism
**Execution.** A tool passes caller-controlled arguments into a shell string or `exec()`/`eval()`: classic command injection, reached through a tool call instead of a web form. The InfoQ analysis attributes **13 of 30** documented CVEs to this. Argument arrays leave nothing to inject into.

**Management.** MCP tooling ships operational surfaces built with dev-tool casualness and left reachable on production networks. Six CVEs are unauthenticated endpoints that should not have been reachable at all.

**Outbound trust.** Unrestricted egress plus a broad credential turns one SSRF into credential theft. CVE-2026-26118 let a malicious URL pull an Azure managed-identity token because nothing constrained the destination or scoped the token.

**Semantic integrity.** Approval can go stale in two ways. A definition changes after review, or the code behind an unchanged definition does. ETUDE reaches 97.6% attack success through tool updates that run outside the model's context, and a validly signed tool still leaked data in every trial against MCPGuard-Dynamic. In a "rug-pull," the tool a reviewer approved is not the tool that later executes, because the server's advertised definition changed. Pinning a canonical hash of the approved definition turns any change into an explicit review event.

## How to apply
- **Audit execution paths first; it is the largest CVE category.** Grep for `shell=True`, `exec()`, `eval()`, and string-built commands; require argument arrays and fail CI on violations.
- **Treat inspectors, test harnesses, and registration endpoints as production services**, with authentication, network isolation, and minimal filesystem access.
- **Put an egress allow-list on every server and scope credentials per tool purpose**, so one leaked token cannot reach everything the server can.
- **Pin tool manifests at registration** with a SHA-256 hash of the canonical definition, and require operator review for any material change.
- **Re-verify tools on every update, not just at first approval.** Signatures prove who published, not what the code does.
- **Bound what each call can see.** Run tool invocations with only the data authorised for their destination, as germline execution does.
- **Add input and context scanning on tool schemas and outputs.** COPEX measured a 49.6% mean drop in attack success on an eight-attack subset; a regex description scanner caught 20 of 45 poisoning scenarios. Treat scanning as partial, not a replacement for the controls above.
- **Budget for controls beyond the gateway.** It provides inbound routing, auth, and observability; execution, outbound, and integrity controls are separate work.

## Failure modes
- Equating "behind an authenticated gateway" with "secure."
- Leaving debug or inspector tooling reachable because it "isn't the real API."
- Giving a tool an outbound credential broader than its one integration, so an SSRF becomes full-credential exfiltration.
- Trusting a server's tool definition or signed code indefinitely after first approval.
- Relying on the model to refuse: frameworks add no defense, so resistance varies from 0.4% to 49.7% by model.

## Related
See [MCP](/topic/mcp), [agent sandboxing](/topic/agent-sandboxing) for execution isolation that complements argument arrays, and [prompt injection](/topic/prompt-injection) for the attacker-controlled input behind outbound-trust failures.
