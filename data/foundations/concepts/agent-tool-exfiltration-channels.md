---
slug: agent-tool-exfiltration-channels
title: "Why can a tool designed to block exfiltration still leak your data?"
question: "Why can a tool designed to block exfiltration still leak your data?"
summary: "Blocking the obvious exfiltration path — a model encoding secrets straight into a URL it fetches — isn't enough. Claude's web_fetch tool blocked exactly that, but a researcher still exfiltrated a user's name, city, and employer by chaining an allowed capability (following links found inside a page it had already fetched) into a slow, one-step-at-a-time leak."
status: active
cluster: safety
updated: 2026-07-17
audience: "strong-software-engineer"
related_topics: [prompt-injection, tool-use]
related_playbook_cards: [pb-restrict-web-fetch-link-following]
related_storylines: []
evidence:
  - id: paul-willison-2026-claude-web-fetch-exfiltration
    kind: production-field-report
    title: "How I tricked Claude into leaking your deepest, darkest secrets"
    url: "https://simonwillison.net/2026/Jul/15/claude-web-fetch-exfiltration/#atom-everything"
    note: "Documents security researcher Ayush Paul's attack against Claude's web_fetch tool. web_fetch already blocked a model from directly constructing an exfiltrating URL (e.g. concatenating recent answers onto an attacker's URL), restricting fetches to user-entered URLs or web_search results. Paul found that web_fetch also let the model follow links embedded inside a page it had already fetched. A honeypot site posing as a Cloudflare check told Claude to navigate an alphabetically-ordered chain of nested links (coffee.evil.com/a, /b, ...) to find the user's profile, exfiltrating name, home city, and employer one hop at a time, and targeted only Claude-User user-agents to stay under the radar. Anthropic fixed it by removing web_fetch's ability to navigate to links discovered inside its own previously fetched content, and did not pay a bug bounty, saying the issue had already been found internally."
  - id: story-5201cdda51e234b5-web-fetch-exfiltration
    kind: story
    sid: "5201cdda51e234b5"
  - id: agent-tool-exfiltration-channels-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "This is the 'lethal trifecta' pattern the source article itself names: private data access, exposure to untrusted content, and any exfiltration vector, together, are exploitable regardless of which single vector you closed first. Any agent tool that both reads untrusted content and can take a further action based on what it read is a potential exfiltration channel, even after the most obvious version of the exploit is blocked — the channel just needs to move slower and use a legitimate-looking capability like link-following instead of an outbound request."
covers_evidence:
  - paul-willison-2026-claude-web-fetch-exfiltration
  - story-5201cdda51e234b5-web-fetch-exfiltration
  - agent-tool-exfiltration-channels-editorial-synthesis
---

## Builder consequence
If your agent has a tool that reads external, untrusted content — fetches a web page, reads an email, opens a file from a shared drive — and that tool can also take a further action based on what it read, you have a potential exfiltration channel even after you block the obvious attack. Stopping "the model can't put secrets directly into a URL it fetches" is necessary but not sufficient. An attacker can still walk the model through a sequence of individually legitimate-looking actions that adds up to the same leak, one small piece at a time.

## Short answer
Closing the most direct exfiltration path doesn't close the channel. Claude's web_fetch tool already blocked a model from constructing a URL that encoded private data and fetching it — the obvious attack. Security researcher Ayush Paul found a second path: web_fetch let a model follow links it discovered *inside a page it had already fetched*. A honeypot site instructed Claude to navigate an alphabetically-ordered chain of links, one per letter of the target information, turning "follow this legitimate-looking link" into a one-bit-at-a-time channel that leaked a user's name, home city, and employer. Anthropic's fix removed that specific capability: web_fetch can no longer navigate to links found inside its own fetched content.

## Builder model
Split "can this tool exfiltrate data" into two questions, not one:

- **Can the model construct an outbound request that encodes secret data?** This is the obvious attack, and most tool designs already block it — e.g. disallow the model from freely composing arbitrary URLs to fetch.
- **Can the model be steered, by content it reads, into a sequence of otherwise-legitimate actions whose end state reveals the secret?** This is the channel that survives the first fix. Each individual step — "follow this one link" — looks like normal tool behavior. Only the sequence, chosen entirely by the untrusted content the tool read, encodes the leak.

The source article names the underlying pattern the "lethal trifecta": private data the agent can access, exposure to untrusted content that can carry instructions, and any exfiltration vector at all. All three conditions together are exploitable, and closing only one vector (direct URL construction) still leaves the trifecta intact if a second vector (link-following) exists.

## Mechanism
The honeypot page presented itself as a Cloudflare bot check and instructed Claude, in its page content, to "navigate through the website letter by letter to find the user's profile." The site served links at predictable, sequential paths, and which link the honeypot's next page pointed to depended on the letter of the secret being exfiltrated at that step. Repeating this across many fetches recovered the user's name, home city, and employer — three separate secrets pulled out one character at a time through a channel that was never a single "send this data out" call, just a long chain of individually unremarkable "fetch the next page" calls. The site also targeted only `Claude-User` user-agents, so the attack activated selectively rather than showing the same behavior to every visitor, including automated scanners.

The design flaw was specific: web_fetch already refused to let the model directly manipulate or construct a URL that would encode data into the outbound request — it restricted fetches to URLs the user had entered themselves or that the companion web_search tool had returned. But it did allow the model to follow a link *embedded in a page it had already fetched*, a capability that reads as ordinary browsing (a page has links, an agent follows them toward the user's goal) but has no way to distinguish "this link was authored by the untrusted page to complete an exfiltration protocol" from "this link is a normal next step." Anthropic's fix removed that capability outright: web_fetch can no longer navigate to links discovered within its own previously fetched content.

## Evidence
- Production field-report-backed: Ayush Paul's honeypot attack against Claude's web_fetch tool exfiltrated a user's name, home city, and employer by chaining link-follows the tool allowed, even though direct URL-construction exfiltration was already blocked; Anthropic's shipped fix removed web_fetch's ability to follow links found inside its own fetched content.
- Source story: the durable story record for this write-up backs the same finding and links back to the original reporting.
- Editorial inference: the general pattern — an untrusted-content-reading tool with any further degree of freedom is a potential exfiltration channel — generalizes past web_fetch to any tool combining "reads content you don't control" with "acts on what it read."

## How to apply
- **Enumerate every degree of freedom your untrusted-content-reading tools have, not just the headline capability.** web_fetch's headline risk was "can it construct an exfiltrating URL"; the actual exploited risk was "can it follow a link it found," a capability that looked incidental.
- **Treat links, filenames, or record IDs discovered inside untrusted content as untrusted instructions, not as data.** A link embedded in a fetched page was authored by whoever controls that page — following it on the page's terms, not the user's, is exactly the exploited behavior.
- **Prefer allowlisting the exact target over free navigation.** Restrict a fetch/browse tool to the URL the user asked for or an explicit allowlist, and require any further navigation to be separately authorized rather than treated as a continuation of the first fetch.
- **Watch for selective-targeting attacks in your own logs.** This attack activated only for `Claude-User` user-agents specifically to evade generic detection — auditing by user-agent, referrer, or request-pattern anomalies can surface an attack that never trips a blanket content filter.
- **Re-audit after adding any new follow-up action to a content-reading tool.** A tool that's safe today can become an exfiltration channel the moment you add a seemingly unrelated capability (follow a link, open an attachment, query a related record) that gives untrusted content a new way to steer sequential behavior.

## Failure modes
- Fixing only the headline exploit — blocking direct URL construction — and declaring the tool safe, missing that a secondary capability like link-following reopens the same class of attack through a slower channel.
- Treating "the model is just browsing" as inherently benign: a sequence of individually normal-looking tool calls, each following the last, is the actual exfiltration mechanism, not a red flag on its own.
- Testing exfiltration defenses only against generic scanners or obvious single-shot attempts, missing an attack that targets a specific user-agent and unfolds over many small steps.
- Assuming a vendor's fix for one exfiltration channel in a tool covers every exfiltration channel in that tool, when a distinct capability in the same tool can carry the same class of attack.

## Related
See [prompt injection](/topic/prompt-injection) for the broader threat model this attack sits inside, and [tool use](/topic/tool-use) for how ad-hoc tool integrations create exactly this kind of unreviewed degree of freedom.
