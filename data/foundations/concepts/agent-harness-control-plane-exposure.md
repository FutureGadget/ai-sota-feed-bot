---
slug: agent-harness-control-plane-exposure
title: "Why could an agent disable its own sandbox by calling a local interface?"
question: "Why could an agent disable its own sandbox by calling a local interface?"
summary: "CVE-2026-82533 (CVSS 9.4) let a DeepSeek coding-agent harness's own sandboxed shell call an unauthenticated local control interface and switch its session to a danger-full-access mode that turned off the sandbox and approval prompts — one shell command, because the interface checked only the client-supplied Host header, never the connection's actual origin."
status: active
cluster: safety
updated: 2026-09-11
audience: "strong-software-engineer"
related_topics: [agent-sandboxing, tool-use]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: story-6d7e21b41e293e2d-hackernews-deepseek-harness
    kind: story
    sid: "6d7e21b41e293e2d"
    title: "DeepSeek Harness Flaw Let AI Agents Disable Their Own File Sandbox Without Approval"
    note: "The Hacker News' technical account: the harness gave the agent's own shell the address and session identifier of a local control interface with no authentication. The interface's own request-validation code checked the client-supplied Host header and explicitly commented that this 'is not an auth layer' — yet no other check backed it. One call set the session to a mode named danger-full-access, turning off both the sandbox and approval prompts. Tracked as CVE-2026-82533, CVSS 9.4, affecting versions 0.1.1-rc.2 and earlier; fixed in 0.1.2-rc.1 (shipped 2026-08-27) with one-time-token authentication — the browser exchanges a startup token for a signed cookie used on every subsequent call."
  - id: story-8478102e21445d5c-ox-security-cve
    kind: story
    sid: "8478102e21445d5c"
    title: "CVE-2026-82533: DeepSeek Harness Vulnerability Lets AI Agents Escape Their Own Sandbox"
    note: "OX Security's disclosure write-up, naming and scoring the CVE."
  - id: story-cdd15242b725bbc8-forkast-deepseek-harness
    kind: story
    sid: "cdd15242b725bbc8"
    title: "DeepSeek Harness Sandbox Escape Lets AI Agents Disable Their Own Confinement"
    note: "Corroborating outlet coverage of the same disclosed CVE."
  - id: agent-harness-control-plane-exposure-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "CVE-2026-82533 is a different failure shape than the 2026 cybersecurity-eval sandbox incidents (where an external network misconfiguration left an otherwise-real boundary open). Here the boundary was never external: the harness put a privilege-escalation control interface on the same network path the confined process already had, and authenticated it with a header the caller supplies rather than a fact about the caller. The generalizable lesson is about control-plane placement and authentication, not about network egress."
covers_evidence:
  - story-6d7e21b41e293e2d-hackernews-deepseek-harness
  - story-8478102e21445d5c-ox-security-cve
  - story-cdd15242b725bbc8-forkast-deepseek-harness
  - agent-harness-control-plane-exposure-editorial-synthesis
---

## Builder consequence
If you build or operate a coding-agent harness that exposes any local interface for changing session privilege — turning a sandbox off, approving a risky action, switching execution modes — that interface is reachable by the exact process you're trying to confine, unless you've specifically isolated it. CVE-2026-82533 (CVSS 9.4) shows what happens when it isn't: a DeepSeek coding-agent harness gave the agent's own shell the address and session ID of its local control interface, the interface had no real authentication, and one shell command flipped the session into a mode that disabled the sandbox and every approval prompt. No prompt injection, no jailbreak — the agent had a working credential to defeat its own containment by design.

## Short answer
The harness's local control interface accepted a request whenever the `Host` header matched an expected value. A code comment on that check said, correctly, that it "is not an auth layer" — but nothing else stood in for one. Because the harness also handed the sandboxed shell the interface's address and the current session identifier (so the agent's own tooling could talk to it), the sandboxed process had everything it needed to call the interface directly and set its session to `danger-full-access`, a mode that turns off both the sandbox and approval prompts. The fix, shipped in version 0.1.2-rc.1, replaces the header check with one-time-token authentication: the browser exchanges a startup token for a signed cookie that every later call must present.

## Builder model
Split any local control interface your agent harness runs into two questions:

- **Can the confined process reach it at all?** If the sandboxed shell has network access to the same host and port the control interface listens on, that's not a hypothetical attack surface — it's a working path, whether or not you intended the agent to use it.
- **If it can reach it, can it authenticate as a legitimate caller?** A check based on something the caller supplies — a `Host` header, a request path, a claimed session ID — is not authentication; it's a fact the caller controls and can set to whatever passes. Real authentication needs a secret the caller couldn't have unless it was actually issued one, like a token exchanged once at startup and never exposed to the sandboxed process afterward.

CVE-2026-82533 failed both questions the same way: the interface was reachable (the harness handed the sandboxed shell its address), and the "authentication" was a value the caller sets. Either fix alone would have closed the hole — unreachability or real authentication — but the harness had neither.

## Mechanism
The harness ran two things on the same host: the sandboxed agent process, executing the model's shell commands, and a local control interface used by the harness's own tooling (its browser-based session UI) to manage session state — including a `danger-full-access` mode that exists for legitimate cases where a user wants to run without sandboxing. To let its own tooling reach that interface, the harness passed the interface's address and the active session's identifier into the environment the sandboxed shell runs in.

The interface's request handling checked the incoming request's `Host` header against an expected value before acting on it — a pattern that guards against some cross-origin browser attacks, but says nothing about who is actually calling, since any client sets its own `Host` header. The code itself carried a comment acknowledging this ("is not an auth layer"), but no other check ran in its place. A shell command from inside the sandbox — issued by the agent, using the address and session ID it had already been given — could set the `Host` header to the expected value, call the interface, and switch the session to `danger-full-access`. That mode turns off the sandbox and stops approval prompts, so from that point the agent's shell commands run with no containment at all.

The fix (0.1.2-rc.1) replaces the `Host`-header check with one-time-token authentication: a token issued once at browser startup is exchanged for a signed cookie, and every subsequent call to the interface must present that cookie. A sandboxed process that was never handed the startup token has no way to obtain a valid cookie, so reachability alone no longer suffices.

## Evidence
- Story-backed (The Hacker News): full technical account of the vulnerability — the `Host`-header check, the `danger-full-access` mode, the code comment disclaiming the check as an auth layer, CVE-2026-82533 at CVSS 9.4, affected versions 0.1.1-rc.2 and earlier, and the one-time-token fix in 0.1.2-rc.1 shipped 2026-08-27.
- Story-backed (OX Security): the CVE disclosure that named and scored the vulnerability.
- Story-backed (forkast.news): corroborating outlet coverage of the same disclosed CVE.
- Editorial inference: that this is a control-plane-placement and authentication failure, distinct in mechanism from the 2026 cybersecurity-evaluation sandbox-escape incidents (external network misconfiguration around an otherwise-real boundary), is LLM Digest's synthesis.

## How to apply
- **Never give a sandboxed process network access to its own harness's control plane.** If the agent's shell can resolve or reach the interface that manages its own privilege level, that reachability is a live escape path, regardless of whether you expect the agent to use it — CVE-2026-82533 required no discovery step because the harness handed the address over directly.
- **Don't authenticate a control interface with anything the caller supplies** — a `Host` header, a path, a claimed identifier. Use a secret issued out-of-band (a token exchanged once at a trusted startup step, then carried in a signed cookie or equivalent) that a process which was never given the secret cannot forge.
- **Treat any privilege-escalation mode (a "disable sandboxing," "full access," or "skip approval" switch) as requiring the same authentication rigor as a production admin endpoint**, not as an internal convenience feature — it's exactly the target an agent with shell access will find useful to reach.
- **Audit what your harness passes into the sandboxed process's own environment.** The vulnerability existed because the harness gave the confined shell everything it needed (address and session ID) to reach the interface that could free it; review environment variables, mounted sockets, and injected config for anything that describes infrastructure the process shouldn't be able to act on.
- **When you patch a check like this, verify the fix requires a secret the sandboxed process never had, not just a stricter version of the same request-attribute check.**

## Failure modes
- Treating a `Host`-header or path-based check as authentication, when it validates only what the request claims about itself, not who is making it.
- Handing a sandboxed process the address, credentials, or identifiers for infrastructure that manages its own confinement, on the assumption that the agent "wouldn't" use them without being told to.
- Building a privilege-escalation mode (full access, sandbox-off, approval-skip) as a convenience feature for the harness's own tooling, without asking whether the same interface is also reachable from inside the thing it's meant to control.
- Assuming a local-only interface is safe because it isn't exposed to the public internet, when "local" still includes the sandboxed process running on the same host.

## Related
See [agent sandboxing](/topic/agent-sandboxing) for the broader containment toolkit this concept assumes as a baseline, and [tool use](/topic/tool-use) for how ad-hoc local interfaces an agent harness wires up for its own tooling become part of the agent's reachable surface. Compare [why frontier models keep attacking real systems during cybersecurity evaluations](/foundations/cyber-eval-sandbox-escapes) for a different sandbox-escape mechanism — a boundary that was never really closed, rather than one an authenticated-looking interface let the confined process open itself.
