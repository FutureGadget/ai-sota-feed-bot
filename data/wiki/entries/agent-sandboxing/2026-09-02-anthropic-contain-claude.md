---
title: "Anthropic matches a different sandbox to each product; custom proxies were the weakest link"
date: 2026-09-02
theme: egress-and-escapes
evidence: [64af1d1a2fd48283]
---
- **claude.ai:** gVisor containers with per-session, non-persistent filesystems.
- **Claude Code:** OS-level sandbox plus an auto-mode classifier catching ~83% of overeager actions. In a red-team test, direct injection to exfiltrate AWS credentials **succeeded 24 of 25 times**; only egress and filesystem controls stopped it.
- **Claude Cowork:** a sealed VM with credentials in the host keychain. A red team still exfiltrated via allowlisted `api.anthropic.com` with an attacker's API key, fixed by an in-VM proxy that accepts only the session's own tokens.

Validate paths after symlink resolution. Anthropic found its custom proxies and allowlist code weaker than battle-tested hypervisors and syscall filters: buy the isolation primitive.
