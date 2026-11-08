---
title: "A Firecracker rebuild of Google's per-session agent microVM shows snapshot forks are cheap on bare metal"
date: 2026-11-08
theme: managed-platforms
evidence: [f88ba1bfaaff2950]
---
Google's Agent Compute Engine gives each agent session its own microVM, checkpointed while the model thinks, cloned copy-on-write from warm snapshots, with no network card. Google published no latency or density numbers and the preview is months away. An independent author rebuilt the pattern on Firecracker (about 2,200 lines of Go) and measured it, self-run: 64 idle forks of a 512 MiB VM cost about 3 MiB of host memory each, and a snapshot restore takes 25 ms, 26x faster than a cold boot.

Under nested virtualization on a Mac mini, twelve concurrent forks never became ready.

For builders: per-session VM isolation is buildable from open parts today, but benchmark on bare metal, not nested virtualization.
