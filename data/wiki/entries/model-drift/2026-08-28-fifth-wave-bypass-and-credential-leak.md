---
title: "SDK one-liners forward another zsh fix, a dangling-operator bypass, and a key leak"
date: 2026-08-28
theme: bundled-cli-bumps
evidence: [d772d2f5565f338a, 74046490d599263e]
---
SDK v0.2.143 and v0.2.144 forward claude-code v2.1.238 and v2.1.246 with single-line changelogs.

- **v2.1.238** improves Bash permission checks for zsh syntax in shell conditionals: the same class of loophole as v2.1.221, patched again.
- **v2.1.246** requires approval for commands with a dangling `&&` or `||`, stops telemetry sending a third-party `ANTHROPIC_BASE_URL` gateway's API key to the wrong host, and makes the sandbox respect `--setting-sources`. It also warns that rules like `Bash(git * main)` match options inserted before the subcommand.
