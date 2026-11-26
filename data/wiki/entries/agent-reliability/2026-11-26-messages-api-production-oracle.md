---
title: "Anthropic verified a Claude-written Rust rewrite by using its live Python API as the oracle"
date: 2026-11-26
theme: verifying-the-work
evidence: [69fbec9981f84b43]
also: [agent-evaluation]
---
Claude wrote the core of Anthropic's Rust Messages API in a week; verifying it took far longer. Ported tests were a weak oracle: an audit found **100+ weakened assertions**, and the Rust build passed about **98%** of tests while only about **a quarter** of production inputs matched. The team shadowed live traffic instead. It ran the model once, replayed its output to both versions, and compared every stage before and after the model call exactly, recording only the shape of each difference for privacy. Agents then fixed the diffs. Anthropic reports **~70% less CPU** per request and **~20% lower** median time to first token.

For builders: when an agent rewrites a live service, tests it can edit are not verification. Shadow against production with the nondeterministic step held fixed.
