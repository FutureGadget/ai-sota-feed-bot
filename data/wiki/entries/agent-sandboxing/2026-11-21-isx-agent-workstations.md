---
title: "isx gives each coding agent its own Incus machine instead of the developer's credentials"
date: 2026-11-21
theme: local-sandboxes
evidence: [7c2df92116551afa]
---
isx (formerly incus-spawn) runs each AI coding agent in its own **Incus system container** on Linux or macOS, built from a reusable template image with the OS, tools, repos, and agent preinstalled. The agent gets full autonomy inside the machine and asks for no approvals, but cannot read the host's API keys, GitHub token, `~/.ssh`, or other checkouts.

The same disposable machines serve for triaging untrusted patches and reproducing bug reports. For builders: a full per-agent machine is an alternative to stacking permission prompts, so you can run several agents in parallel unattended while credentials stay on the host.
