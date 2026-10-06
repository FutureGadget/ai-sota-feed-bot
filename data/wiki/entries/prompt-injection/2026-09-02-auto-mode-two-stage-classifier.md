---
title: "Claude Code Auto Mode pairs an injection probe with a two-stage action classifier"
date: 2026-09-02
theme: harness-controls
evidence: [d5f9dbd62b3ecc11]
---
Users approve **93%** of Claude Code's permission prompts, so Anthropic built Auto Mode as two layers:

- An input probe scans tool outputs for injected instructions and prepends a skepticism warning.
- A Sonnet 4.6 classifier sees only the user's messages and the pending tool call, with assistant text and tool results stripped so it can't be talked round. A fast single-token stage over-blocks (8.5% false positives on 10,000 real-traffic samples); flagged cases go to a chain-of-thought stage that cuts false positives to 0.4%.

The two-stage design misses **17%** of real overeager actions, versus 6.6% for stage one alone. Blocked actions return as tool results with a safer path; a human is pulled in after 3 consecutive or 20 total denials.
