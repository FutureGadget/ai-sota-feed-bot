---
title: "A debug setting in Meta's Muse client let local malware steal its auth token, then inject prompts"
date: 2026-09-26
theme: injection-paths
evidence: [200b2d2e1357f4e9]
---
Patrick Wardle found a zero-day in Meta's Muse desktop client for macOS. An undocumented debug preference (`endo_voyager_dictation_endpoint`), changeable by unprivileged local software without an OS prompt, redirected voice-dictation traffic to an attacker's server. That traffic carried raw audio and the user's **valid Muse auth token**. The attacker could then prompt-inject the hijacked session to run background tasks such as document exfiltration and message-history theft. Meta's fix removed the preference from production builds.

The flaw was not in the model. A configuration surface redirected the channel a credential travels over, and injection did the rest.
