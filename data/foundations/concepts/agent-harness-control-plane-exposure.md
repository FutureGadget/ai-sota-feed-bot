---
slug: agent-harness-control-plane-exposure
title: "Why could an agent disable its own sandbox by calling a local interface?"
question: "Why could an agent disable its own sandbox by calling a local interface?"
summary: "CVE-2026-82533 (CVSS 9.4) let a DeepSeek coding-agent harness's sandboxed shell call an unauthenticated local control interface and switch off its own sandbox and approval prompts, because the interface trusted a caller-supplied Host header instead of a secret."
status: active
cluster: safety
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [agent-sandboxing, tool-use]
related_playbook_cards: [pb-audit-debug-flags-permission-bypass]
related_storylines: []
evidence:
  - id: story-6d7e21b41e293e2d-hackernews-deepseek-harness
    kind: story
    sid: "6d7e21b41e293e2d"
    title: "DeepSeek Harness Flaw Let AI Agents Disable Their Own File Sandbox Without Approval"
    added: 2026-09-12
    note: "The Hacker News' technical account. The harness gave the agent's shell the address and session ID of an unauthenticated local control interface. Its only check was the client-supplied Host header, commented in code as 'not an auth layer'. One call set the session to danger-full-access, disabling sandbox and approvals. CVE-2026-82533, CVSS 9.4, versions 0.1.1-rc.2 and earlier; fixed in 0.1.2-rc.1 (2026-08-27) with a one-time startup token exchanged for a signed cookie."
  - id: story-8478102e21445d5c-ox-security-cve
    kind: story
    sid: "8478102e21445d5c"
    title: "CVE-2026-82533: DeepSeek Harness Vulnerability Lets AI Agents Escape Their Own Sandbox"
    added: 2026-09-12
    note: "OX Security's disclosure write-up, naming and scoring the CVE."
  - id: story-cdd15242b725bbc8-forkast-deepseek-harness
    kind: story
    sid: "cdd15242b725bbc8"
    title: "DeepSeek Harness Sandbox Escape Lets AI Agents Disable Their Own Confinement"
    added: 2026-09-12
    note: "Corroborating outlet coverage of the same disclosed CVE."
  - id: story-200b2d2e1357f4e9-infoq-meta-muse-zeroday
    kind: story
    sid: "200b2d2e1357f4e9"
    title: "Un-Mused: How a Single Debug Setting Bypassed macOS Security in Meta's AI Client"
    added: 2026-09-26
    note: "InfoQ on Patrick Wardle's disclosure: Meta's Muse macOS client shipped an undocumented debug preference, endo_voyager_dictation_endpoint, that any unprivileged local process could overwrite without an OS prompt. That rerouted dictation audio plus the account auth token to an attacker server, and could chain with prompt injection to exfiltrate local files via the TCC-permissioned assistant. Meta's hotfix removed the preference from production builds; no CVE was filed."
  - id: agent-harness-control-plane-exposure-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-09-12
    note: "Unlike the 2026 cyber-eval sandbox incidents, where an external network misconfiguration left a real boundary open, here the harness put its own privilege-escalation interface on a path the confined process already had and authenticated it with a value the caller supplies. Muse extends the lesson to config: a writable value that steers a privileged assistant is a control plane too. The lesson is control-plane placement and authentication, not network egress."
---

## Builder consequence
Any local interface your harness uses to change session privilege (disable sandbox, skip approval, switch mode) is reachable by the process you are confining unless you isolate it. In CVE-2026-82533 (CVSS 9.4), one shell command from the agent's own sandbox turned off the sandbox and every approval prompt. No prompt injection was needed. Writable local config that steers a privileged agent is the same kind of control surface.

## Short answer
The DeepSeek harness gave the sandboxed shell the control interface's address and the session ID, so its own tooling could use them. The interface accepted any request whose `Host` header matched an expected value. A code comment said that check "is not an auth layer", and nothing else stood in for one. The agent could therefore call the interface and set its session to `danger-full-access`. The fix in 0.1.2-rc.1 requires a one-time startup token exchanged for a signed cookie, a secret the sandbox never sees.

## Builder model
Ask two questions of every control surface in your harness:

- **Can the confined process reach it?** If the sandboxed shell can reach the host and port, or write the file, it is a working path whether or not you meant the agent to use it.
- **Can it authenticate as a legitimate caller?** A `Host` header, path, or claimed session ID is something the caller sets. Authentication needs a secret the caller only has if it was issued one.

Either answer being "no" closes the hole. CVE-2026-82533 failed both. Meta's Muse client failed both through a config file: any local process could write the preference, and the client trusted whatever was on disk.

## Mechanism
**Network control plane.** The harness ran the sandboxed agent and a local control interface on the same host. The interface served the harness's browser UI and included a `danger-full-access` mode for users who want to run unsandboxed. To let tooling reach it, the harness exported the interface address and session ID into the sandboxed shell's environment.

A `Host`-header check blocks some cross-origin browser attacks, but it says nothing about who is calling, because every client sets its own `Host` header. The agent could send the expected value, call the interface, and flip its mode. From then on its commands ran with no containment.

The token-and-cookie fix changes what reachability buys. A process that was never handed the startup token cannot mint a valid cookie, so being on the same host is no longer enough.

**Config control plane.** Muse read `endo_voyager_dictation_endpoint`, the server that receives dictation audio, from storage any unprivileged user could write. It trusted the value with no signature or default check. Overwriting it redirected microphone audio and the account auth token to an attacker. Because Muse held broad macOS permissions, prompt injection over the hijacked channel could also pull local files. Meta's fix removed the setting from production builds instead of authenticating writes to it.

## How to apply
- **Keep the control plane off the sandbox's network path.** The confined shell should not be able to resolve or reach the interface that manages its own privilege.
- **Authenticate with an out-of-band secret,** such as a token exchanged once at trusted startup and then carried in a signed cookie. Never with a header, path, or identifier the caller supplies.
- **Treat every escalation mode** ("full access", "sandbox off", "skip approval") like a production admin endpoint, not an internal convenience.
- **Audit what you inject into the sandbox:** environment variables, mounted sockets, and config that describe infrastructure the process should not act on.
- **Verify a patch requires a secret** the sandboxed process never had, not a stricter version of the same request-attribute check.
- **Strip debug and diagnostic config keys from production builds** if an unprivileged process can write them and they redirect endpoints or widen permissions.

## Failure modes
- Treating a `Host`-header or path check as authentication.
- Handing the sandbox addresses or identifiers for the infrastructure that confines it, assuming the agent "wouldn't" use them.
- Building an escalation mode for the harness's own tooling without asking whether the confined process can reach it too.
- Assuming "local-only" means safe, when local includes the sandboxed process on the same host.
- Shipping a writable debug config key that steers a privileged client, assuming the file is as protected as the app that reads it.

## Related
See [agent sandboxing](/topic/agent-sandboxing) for the baseline containment toolkit and [tool use](/topic/tool-use) for how harness-internal interfaces become agent-reachable surface. Compare [cyber-eval sandbox escapes](/foundations/cyber-eval-sandbox-escapes), where the boundary was never closed rather than opened from inside.
