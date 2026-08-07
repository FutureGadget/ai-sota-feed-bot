---
slug: mcp-security-control-layers
title: "What actually breaks when you run MCP in production, and how do you defend it?"
question: "What actually breaks when you run MCP in production, and how do you defend it?"
summary: "An analysis of documented MCP CVEs found most incidents cluster in four layers — unsafe tool execution, unauthenticated management endpoints, unrestricted outbound calls, and undetected tool-definition drift — and a gateway alone defends none of them; each layer needs its own control, enforced closer to the failure than the gateway."
status: active
cluster: safety
updated: 2026-08-07
audience: "strong-software-engineer"
related_topics: [mcp, agent-sandboxing, prompt-injection]
related_playbook_cards: []
related_storylines: [gateway-mcp]
evidence:
  - id: infoq-mcp-defense-in-depth
    kind: production-field-report
    title: "Securing MCP in Production: Defense-in-Depth Beyond the Gateway"
    url: "https://www.infoq.com/articles/securing-mcp-production-gateway/"
    note: "Analyzes documented MCP CVEs and groups the failures into four architectural layers: safe tool execution (13 of 30 documented CVEs traced to unsafe execution patterns like shell string interpolation or exec()/eval() on user input), management infrastructure (six CVEs from unauthenticated inspector, testing-harness, or registration endpoints), the outbound trust boundary (illustrated by CVE-2026-26118, an Azure SSRF that let a malicious URL exfiltrate a managed-identity token), and semantic integrity (undetected post-registration changes to a tool's definition, a 'rug-pull' attack). Recommends per-layer controls: arguments passed as arrays rather than shell strings; mandatory auth plus network isolation on management endpoints; egress allow-lists and per-tool-purpose scoped credentials; and manifest pinning with SHA-256 canonicalization so a definition change requires operator review."
  - id: aws-agentcore-mcp-2026-07-28-spec
    kind: story
    sid: b734d716b0d66f96
    title: "How AgentCore Gateway supports the MCP 2026-07-28 spec"
    note: "Context: this security guidance was published one day after MCP's largest spec revision, framing production hardening as the necessary complement to the new spec's own authorization changes rather than something the spec update handles on its own."
  - id: mcp-security-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "The through-line across all four layers is that a routing gateway sits at the network edge, while three of the four failure classes (unsafe execution, outbound exfiltration, definition drift) originate inside or behind the MCP server itself — a gateway can enforce inbound auth and rate limits, but it structurally cannot see what a tool does once a call reaches it."
covers_evidence:
  - infoq-mcp-defense-in-depth
  - aws-agentcore-mcp-2026-07-28-spec
  - mcp-security-editorial-synthesis
---

## Builder consequence
If "securing MCP" in your deployment plan means "put it behind an authenticated gateway," you've covered one layer and left three uncovered. An analysis of documented MCP CVEs found that most incidents happen inside or downstream of the server the gateway is fronting — in how a tool executes its arguments, what a server can reach outbound, and whether a tool's definition still matches what was approved — none of which a gateway's inbound auth check inspects.

## Short answer
Documented MCP vulnerabilities cluster into four layers, each with a different earliest point where it can actually be stopped: unsafe tool execution (arguments reaching a shell or `eval()`), unauthenticated management surfaces (inspectors, test harnesses, registration endpoints treated as non-production), an unrestricted outbound trust boundary (a server able to call any URL with a privileged credential), and undetected semantic drift (a tool's definition changing after a human approved it). A gateway sitting in front of MCP traffic addresses none of these directly — it's an inbound routing and auth control, and three of the four failure classes happen behind it.

## Builder model
Don't model MCP security as "gateway secures the perimeter, servers are trusted inside it." Model each MCP server as a small privileged service with its own attack surface, and ask the same four questions you'd ask of any service that executes instructions and calls the network: does it turn caller-supplied arguments into a shell command or eval'd code (execution layer)? Are its non-production interfaces — the ones a developer or CI pipeline hits, not the ones an agent hits — actually authenticated (management layer)? What can it reach outbound, and with what credential (trust-boundary layer)? And is there any way for its advertised behavior to change without someone noticing (integrity layer)? A gateway answers "who's allowed to call this server," which is a real but separate question from all four.

## Mechanism
The execution layer fails when a tool implementation passes caller-controlled arguments into a shell string or an `exec()`/`eval()` call instead of an argument array — the classic command-injection pattern, just reached through a tool call instead of a web form. The InfoQ analysis attributes 13 of 30 documented CVEs to exactly this pattern, and the fix is mechanical: pass arguments as arrays so there's no string to inject into, and gate merges with CI checks that flag `subprocess(shell=True)` and equivalents.

The management-infrastructure layer fails because MCP tooling ships operational surfaces — inspectors, testing harnesses, server registration endpoints — that get built and deployed with the same casualness as any dev tool, then left reachable in a production network because nobody treated them as production. Six documented CVEs trace to exactly this: an unauthenticated management endpoint that shouldn't have been reachable at all. The fix is treating every management endpoint as production-adjacent: mandatory authentication, network isolation, and minimal filesystem access, not "it's just for debugging."

The outbound trust-boundary layer fails when a server's egress isn't restricted and its outbound credential is broader than the one call that needs it. CVE-2026-26118, an Azure SSRF, is the concrete case: a server could be induced to call an attacker-controlled URL and leak a managed-identity token to it, because nothing constrained where the server's outbound calls could go or scoped the credential attached to them. The fix is an egress allow-list enforced at the network layer plus scoped identity tokens — one credential class per tool purpose, so a leaked token from one tool doesn't grant everything the server can do.

The semantic-integrity layer fails when a tool's definition changes after a human or system approved it — a "rug-pull," where the tool a reviewer signed off on isn't the tool that ends up executing. The defense is manifest pinning: hashing the approved tool definition (SHA-256 canonicalization) at registration time, storing that as the signed baseline, and routing any material schema change through operator review instead of silently accepting whatever the server now advertises.

## Evidence
- Production field-report: the InfoQ analysis is grounded in a documented CVE count (30 total, with the 13/6 split cited above) and a specific named vulnerability (CVE-2026-26118), not a hypothetical threat model — it's a measured accounting of what has actually gone wrong in shipped MCP deployments.
- Story-backed: the AWS AgentCore writeup situates this guidance as landing the day after MCP's 2026-07-28 spec revision, which hardened the *authorization* spec but left execution, management-surface, outbound, and integrity risks to be addressed by deployment-level controls, not the protocol itself.
- Editorial inference: the "gateway can't see three of the four layers" framing is LLM Digest's synthesis of why defense-in-depth applies here specifically — it's not a claim made verbatim in either source.

## How to apply
- **Audit tool execution paths for shell/eval usage first — it's the largest documented category.** Grep tool-implementation code for `shell=True`, `exec()`, `eval()`, or string-built shell commands, and require arguments to be passed as arrays instead.
- **Treat your MCP inspector, test harness, and registration endpoint as production services**, not developer conveniences — put authentication and network isolation on them even if "only internal tools use them."
- **Put an egress allow-list on every MCP server's network path, and scope credentials per tool purpose.** A server that only needs to call one internal API shouldn't hold a credential broad enough to reach arbitrary external URLs.
- **Pin tool manifests at registration and diff on every change.** Hash the approved tool definition and require operator review before accepting a materially changed schema from a server you've already approved — don't silently trust whatever the server advertises on each connection.
- **Don't stop at the gateway.** A vendor gateway tier gives you inbound routing, auth, and observability; budget separately for execution-layer, outbound, and integrity controls, because the gateway's threat model doesn't cover them.

## Failure modes
- Equating "behind an authenticated gateway" with "secure": the gateway controls who can call a server, not what the server does with the call once it arrives.
- Shipping debug/inspector tooling to production reachability because it "isn't the real API" — six documented CVEs are exactly this mistake.
- Granting a tool's outbound credential broader scope than the one integration it needs, so a single SSRF or injection turns into full-credential exfiltration instead of a contained one.
- Trusting a server's currently-advertised tool definition indefinitely after initial approval, with no re-verification if that definition changes later.

## Related
See [MCP](/topic/mcp) for the protocol's broader production adoption arc, [agent sandboxing](/topic/agent-sandboxing) for execution-isolation techniques that complement the execution-layer fix here, and [prompt injection](/topic/prompt-injection) for the attacker-controlled-input side of the outbound-trust-boundary failure.
