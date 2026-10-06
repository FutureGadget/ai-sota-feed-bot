---
title: "GKE Agent Substrate targets 10x sandbox density with sub-500ms resume, and GKE scales to zero"
date: 2026-10-03
theme: fleet-density
evidence: [72249bd53d8a5849]
---
Google's September AI-infrastructure update adds the open-source **GKE Agent Substrate**, aimed at millions of sandboxes at **10x the density** of standard container runtimes. Google claims sub-500ms resume, over 500 suspend/resume activations per second, and kernel- and network-level isolation. GKE also now scales workloads to zero natively, through the HPA with KEP-2021 support.

These are vendor-reported targets. The pattern they point to: suspend idle agent sandboxes and resume them on demand instead of keeping them warm, so an idle fleet stops holding capacity.
