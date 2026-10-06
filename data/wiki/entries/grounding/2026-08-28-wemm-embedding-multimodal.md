---
title: "Tencent's WeMM-Embedding-9B embeds text, images, video, and documents in one space"
date: 2026-08-28
theme: better-retrievers
evidence: [a74f114f24afad46]
---
Tencent released **WeMM-Embedding-9B** on Hugging Face. Built on Qwen3.5, it embeds text, images, video, and visual documents into one 4,096-dimension space. It scores **80.6 average on MMEB-v2** (78 datasets), ahead of Qwen3-VL-Embedding's 77.8, and 59.5 on the harder MMEB-v3 (190 tasks).

A retriever that natively embeds slide decks and chart-heavy pages can reach multimodal evidence without a separate extraction pass.
