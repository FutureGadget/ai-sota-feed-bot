---
title: "Tenstorrent accelerators join vLLM as an out-of-tree platform plugin"
date: 2026-09-09
theme: day-0-support
evidence: [d30ab09b3c362794]
---
Tenstorrent joins vLLM as an **out-of-tree platform plugin** built around the hardware's mesh architecture: phase-based scheduling, single-process data parallelism on Galaxy, on-device sampling with a host fallback, and async decode overlap.

A plugin path lets non-NVIDIA hardware run the same serving engine without a fork, which widens the hardware options for a vLLM-based stack.
