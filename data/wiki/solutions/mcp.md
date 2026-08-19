---
slug: mcp
kind: solution
title: "Model Context Protocol: a standard interface for agent tools"
status: active
obstacles: [tool-use]
related_storylines: []
evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55, 2b0cc93ba8a0f9b8, 3c227e4c9b2cd2eb, 2e309060a5831bee, 49c783dfceab27fd, 2ae1f6b53f88576c, 916521ba0baad7c0, b734d716b0d66f96, 9352c956aa90126f, e19273caeeed853d, 89bc6f5296e6a019, ea850b1a9c912609, 793d1e28a9d4d499, 4daf9a3fc6b23a4c, cfcd5af1b5266bac, 801edb72737f6642, e3560887ce822a61]
updated: 2026-08-19
covers_evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55, 2b0cc93ba8a0f9b8, 3c227e4c9b2cd2eb, 2e309060a5831bee, 49c783dfceab27fd, 2ae1f6b53f88576c, 916521ba0baad7c0, b734d716b0d66f96, 9352c956aa90126f, e19273caeeed853d, 89bc6f5296e6a019, ea850b1a9c912609, 793d1e28a9d4d499, 4daf9a3fc6b23a4c, cfcd5af1b5266bac, 801edb72737f6642, e3560887ce822a61]
---

## TL;DR
The Model Context Protocol (MCP) is a standard way to describe, discover, and
call tools so any MCP-speaking agent can use any MCP server. It collapses the
N×M problem of bespoke integrations into a common interface — the agent
equivalent of "speak HTTP" instead of writing a custom client per service.

## State of the art
MCP is moving from a client-side convenience to **production infrastructure**.
Vendors are shipping official servers — HashiCorp's Terraform MCP server reached
GA so agents can drive Terraform Registry APIs, and reference builds wire up SaaS
servers (Amazon Quick, Cisco Webex) into working assistants.

The actuation surface is expanding to the **browser**: WebMCP is in Chrome
origin trials, letting a site expose JavaScript functions and HTML forms as
tools to an in-page agent. The open-source client side is filling in
alongside the browser trial, with MIT, framework-free libraries (Persona.js)
that ship native WebMCP so any site can build agentic experiences without a
vendor SDK. A second browser vendor is now shipping the same surface as a
platform feature rather than a library: Cloudflare previewed automatic
WebMCP support that any site turns on from a dashboard toggle, no code
change required, letting an in-browser agent interact with an unmodified
page — the origin-trial pattern moving from "a team opts in" to "an operator
flips a switch."

MCP is also becoming the assumed plug for **hosted runtimes** — Azure
Functions' agents runtime gives every agent MCP server access (alongside
1,400+ connectors) out of the box — and the long tail keeps filling in with
small task servers (e.g. a "coding tools" MCP that hands any agent file/shell
coding primitives, and an AGPL-licensed search MCP built on Cloudflare AI
Search so an agent can look up project-specific reference material instead
of relying on what's already in its context).

Crucially, the protocol's growth is forcing the **governance** layer —
Claude's enterprise managed authorization provisions MCP connectors org-wide
through an identity provider (Okta first), so connector access and
authorization are configured centrally rather than per user. That move from
"connect a tool" to "govern a fleet of connectors" is the sign of a maturing
standard.

A parallel control targets the **server side of the connection** rather
than who connects: Cloudflare's WriteGuard (private beta) adds
fine-grained security controls to MCP servers themselves — governing what
actions a connected agent's tool calls are allowed to take, not just which
servers it may reach — sharpening the auth story above (who connects) with
a permissions story (what the connection is then allowed to do) at the
layer MCP servers themselves control (see [agent
sandboxing](/topic/agent-sandboxing) for the same write-scoping instinct
applied to sandboxes rather than servers).

The same maturation is landing in the client tooling: Claude Code added
`claude mcp login` / `logout` to authenticate servers from the CLI without
the interactive menu, and practitioners increasingly argue MCP's *core*
value is exactly this — isolating the **auth flow** outside the agent's
context window (and ideally out of the harness entirely) rather than the
tool-description format itself. Read that way, the durable win of MCP is
credential handling, not schema standardization.

That governance push is now backed at the **protocol** level: the MCP
project promoted its Enterprise-Managed Authorization extension to stable
status, replacing per-server consent prompts with a single sign-on flow
through an org's identity provider. It generalizes what Claude's enterprise
auth already did for one vendor into a spec any MCP client or server can
implement.

The auth maturation is also spreading to a **second client**: OpenAI's Codex
CLI 0.144.0 lets MCP tools request interactive authentication without an
experimental opt-in flag, the same "auth flow isolated from the harness"
pattern Claude Code's `mcp login`/`logout` already shipped, now landing
outside Anthropic's own tooling.

The protocol itself just crossed a bigger threshold than any single vendor
feature: the **MCP 2026-07-28 specification** is the largest revision since
launch, making the protocol **stateless** and adding a governed extensions
system alongside hardened authorization — a foundational rewrite of how
clients and servers interoperate, not another connector. AWS's AgentCore
Gateway already supports the new spec, giving platform teams a concrete
reference implementation for what adopting it looks like in a managed
gateway rather than a bespoke client patch.

Production security guidance is maturing alongside the spec: an InfoQ field
guide lays out **defense-in-depth for MCP in production** across four
architectural layers — safe execution, management infrastructure, outbound
network calls, and the gateway itself — treating "securing MCP" as a layered
architecture decision rather than a single gateway config toggle. It is the
production-hardening counterpart to the governance and auth work below (see
[prompt injection](/topic/prompt-injection) and
[agent sandboxing](/topic/agent-sandboxing) for the attack surface this
defends against).

The statelessness change is also drawing developer skepticism, not just
adoption: dropping the initialize handshake and session header in favor of
required method and tool-name headers reads to some practitioners as MCP
converging back toward "just an API." That reaction sharpens what the
protocol's durable value actually is: the shared tool-description and
discovery layer this page tracks, not the stateful session the new spec just
removed — a distinction worth stating plainly now that statelessness has
made the two easy to conflate.

Two further signs of maturation:

- **Tool discovery is becoming a scaling problem** — as a single agent faces dozens of connectors, listing every tool schema blows the context budget, so clients are shifting to *search* over the registry; OpenAI's Codex now uses MCP tool search by default, treating "find the right tool" as a retrieval step rather than dumping the full catalog.
- **What MCP carries is widening beyond tools**: reference data and memory now ride the same protocol — Mozilla's MDN MCP service (and community spinoffs that repackage browser-compat data as a queryable SQLite-backed server) expose knowledge, while Elastic's Atlas serves *agent memory* over MCP — so MCP is becoming the generic plug for tools, data, and state alike.

That "more than tools" widening now includes **work distribution**: TaskPeace
is a task queue that coding agents pull work *from* over MCP, using the
protocol as the plug for a job queue rather than a single tool call or a
data/memory fetch — a third payload type alongside tools and knowledge/state.

The widening reaches **symbolic computation** too: Euclid-MCP puts a full
SWI-Prolog engine behind the protocol, so an LLM client delegates
deterministic logical inference instead of reasoning it out itself. It
introduces Euclid-IR, an engine-agnostic intermediate representation for
Horn-clause logic that's LLM-generatable and compiles to Prolog (or other
backends), and exposes a translate-run-inspect-repair tool loop so the
client keeps full access to proof traces and derivation logs rather than a
black-box answer. On a compliance-sensitive IT security use case, LLMs alone
hold up on small knowledge bases but hallucinate systematically as they
grow, while Euclid-MCP returns exact answers with lower latency and more
compact output — the authors argue semantic RAG is structurally unsuited to
rule enforcement, positioning an MCP server, not the model, as the shared
reasoning substrate for both RAG assistants and agentic systems.

Tool **definition design** is now a subject in its own right, separate from
the auth/governance work above. AWS's field guide names two failure modes —
bloated context (every tool schema loads on every call, whether used or
not, contributing to context rot) and confusion (vague parameter names and
oversized result payloads make the model call the wrong tool or the right
tool wrong) — and walks a concrete progression from V1 (raw API exposed
as-is) through richer descriptions, `Literal`-typed schema constraints, and
lazy-loaded taxonomies (a separate discovery tool fetched only when needed)
to a leanest-baseline design that cut per-turn context usage from 4% to 2%.
The same guide cites Anthropic's own lazy-loading work reaching up to 85%
token reduction, and recommends capping tool parameter counts at roughly
eight. This is the tool-schema-quality half of the [context-compaction](/topic/context-compaction)
problem: cutting the tokens a tool *definition* burns, not the tokens a
conversation accumulates.

Two production deployments show the protocol carrying **non-tool payloads**
into everyday enterprise workflows rather than just connecting an API.
Dropbox wired MCP into its internal knowledge platform, Dash, so an
AI-assisted code review can pull the threat model and security requirements
for a pull request and check the implementation against design intent —
security context riding the same protocol as a tool call (see [prompt
injection](/topic/prompt-injection)). Amazon Bedrock AgentCore uses
pre-built MCP server connectors, plus fine-grained access control and
persistent memory, to let an agent query multiple business data sources in
natural language while automatically enforcing role-based boundaries —
cross-system business intelligence assembled from configuration rather than
custom integration code.

A cloud-vs-local gap gets a concrete bridge: AWS built a secure MCP bridge
that lets a cloud-hosted Bedrock AgentCore agent call MCP servers running on
a user's own laptop, tunneling signed messages over an existing WebSocket
connection through a browser extension and Chrome native messaging — no open
inbound ports or VPN required. It is the reverse direction of the usual MCP
story (a cloud agent reaching local tools and files rather than a local agent
reaching a cloud API), addressing the "AgentCore runs in the cloud, but the
user's tools live on their laptop" gap directly.

Governance is also consolidating at the **cloud gateway** layer, not just
inside the protocol's own auth extensions: Azure API Management shipped a
dedicated AI Gateway tier whose control plane is organized around models,
MCP servers, and tools — not REST APIs — fronting Foundry, Bedrock, Vertex
AI, and OpenAI behind one policy surface. It puts MCP server governance next
to model governance in the same managed product, the tool-fleet counterpart
to AWS's Claude Apps Gateway spend-and-telemetry control plane.

## What's new
Cloudflare's WriteGuard (private beta) adds fine-grained security controls
to MCP servers themselves — governing what a connected agent's tool calls
may do, not just who may connect — a server-side permissions layer
alongside this page's standing client-auth governance thread (see State of
the art above).

Prior update: Cloudflare previewed automatic WebMCP support (a dashboard toggle, no code
change) — the second browser vendor shipping the actuation surface this page
tracks. Separately, the MCP 2026-07-28 statelessness change is drawing
developer pushback alongside its adoption: dropping the session handshake
for header-based routing reads to some practitioners as convergence toward
a plain API, which sharpens what MCP's durable value actually is (shared
tool description and discovery, not the session state removed).

Prior update: Azure API Management shipped a dedicated AI Gateway tier governing models,
MCP servers, and tools from one control plane in front of Foundry, Bedrock,
Vertex AI, and OpenAI — a second cloud vendor putting MCP governance behind
a managed gateway, next to AWS's Claude Apps Gateway.

## Trade-offs
A shared protocol buys interoperability and reuse, but every connector you expose
is a new permission and a new attack surface — MCP standardizes *access*, which
makes authorization and blast-radius the hard part (see
[prompt injection](/topic/prompt-injection)). It also adds a moving dependency:
server quality, versioning, and uptime become yours to manage, and a misbehaving
or malicious server is now reachable by every agent that speaks the protocol.
Best when you have many tools and many agents; overkill for a single hardcoded
integration.

## Why it matters for platform engineers
MCP is the integration layer you adopt instead of writing API wrappers — it
turns tool connectivity into a fleet you provision and govern (identity-provider
auth, per-connector permissions) rather than scattered glue code. The platform
job shifts accordingly: from building connectors to running a connector
registry safely, which is squarely an infra-and-security responsibility.
