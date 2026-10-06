---
slug: agent-tool-exfiltration-channels
title: "Why can a tool designed to block exfiltration still leak your data?"
question: "Why can a tool designed to block exfiltration still leak your data?"
summary: "Blocking the obvious path, a model encoding secrets into a URL it fetches, is not enough. Claude's web_fetch blocked that, yet a researcher still leaked a user's name, city, and employer by chaining an allowed capability: following links inside fetched pages."
status: active
cluster: safety
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [prompt-injection, tool-use]
related_playbook_cards: [pb-restrict-web-fetch-link-following]
related_storylines: []
evidence:
  - id: paul-willison-2026-claude-web-fetch-exfiltration
    kind: production-field-report
    title: "How I tricked Claude into leaking your deepest, darkest secrets"
    url: "https://simonwillison.net/2026/Jul/15/claude-web-fetch-exfiltration/#atom-everything"
    sid: "5201cdda51e234b5"
    added: 2026-07-17
    note: "Ayush Paul's attack on Claude's web_fetch, which already limited fetches to user-entered URLs or web_search results. web_fetch could still follow links inside fetched pages. A honeypot posing as a Cloudflare check had Claude walk alphabetically ordered nested links, leaking name, home city, and employer one hop at a time, and targeted only Claude-User user-agents. Anthropic removed link-following from fetched content and paid no bounty, saying it had found the issue internally."
  - id: agent-tool-exfiltration-channels-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-07-17
    note: "This is the 'lethal trifecta' the source names: private data access, exposure to untrusted content, and any exfiltration vector together are exploitable whichever single vector you close first. Any tool that reads untrusted content and can act on what it read is a potential exfiltration channel, even after the obvious exploit is blocked; the channel just moves slower through a legitimate-looking capability such as link-following."
---

## Builder consequence
If an agent tool reads untrusted content (a web page, an email, a shared file) and can take a further action based on it, you have a potential exfiltration channel even after blocking the obvious attack. Stopping the model from putting secrets into a URL is necessary but not sufficient. An attacker can walk the model through individually legitimate actions that add up to the same leak, one small piece at a time.

## Short answer
Closing the most direct exfiltration path does not close the channel. Claude's `web_fetch` already blocked the model from fetching a URL it built to encode private data. Ayush Paul found a second path: `web_fetch` could follow links found *inside a page it had already fetched*. A honeypot steered Claude through a chain of letter-indexed links and leaked a user's **name, home city, and employer**. Anthropic's fix removed link-following from fetched content.

## Builder model
Ask two questions of every content-reading tool:

- **Can the model build an outbound request that encodes a secret?** This is the obvious attack. Most designs block it, for example by forbidding free-form URLs.
- **Can content the tool reads steer it into a sequence of legitimate actions whose path reveals the secret?** This survives the first fix. Each step ("follow this link") looks normal; only the sequence, chosen by the untrusted page, encodes the leak.

The source calls the underlying pattern the **lethal trifecta**: private data, untrusted content that can carry instructions, and any exfiltration vector. Closing one vector leaves the trifecta intact if another exists.

## Mechanism
**The sequence is the signal.** If untrusted content chooses which link the agent follows next, and that choice depends on a secret the agent knows, the server's access log spells out the secret. No single request carries data. In Paul's attack, a page posing as a Cloudflare bot check told Claude to "navigate letter by letter" to find the user's profile. Repeated fetches over predictable paths recovered three secrets character by character.

**Allowed capabilities can be indistinguishable from attacks.** `web_fetch` restricted fetches to user-entered URLs or `web_search` results, which blocked direct URL construction. Following a link inside a fetched page reads as ordinary browsing. The tool cannot tell "the page authored this link to run an exfiltration protocol" from "this is the natural next step". Anthropic removed the capability rather than trying to classify links.

**Selective targeting evades generic scanning.** The honeypot activated only for `Claude-User` user-agents. Scanners and human visitors saw nothing unusual, so blanket content filtering would not have caught it.

## How to apply
- **List every degree of freedom** your untrusted-content tools have, not just the headline capability. The exploited one here looked incidental.
- **Treat links, filenames, and record IDs found in untrusted content as instructions,** not data.
- **Restrict navigation to the user's requested URL or an explicit allowlist,** and require separate authorization for any further hop.
- **Watch logs for selective targeting** by user-agent, referrer, or request-pattern anomalies.
- **Re-audit whenever you add a follow-up action** (follow a link, open an attachment, query a related record) to a content-reading tool.

## Failure modes
- Blocking direct URL construction and declaring the tool safe while a secondary capability reopens the channel.
- Treating "the model is just browsing" as benign when the browsing sequence is the exfiltration mechanism.
- Testing only against generic scanners or single-shot attempts, missing a targeted, many-step attack.
- Assuming a vendor's fix for one channel covers every channel in the same tool.

## Related
See [prompt injection](/topic/prompt-injection) for the threat model this attack sits inside, and [tool use](/topic/tool-use) for how ad-hoc tool integrations create unreviewed degrees of freedom.
