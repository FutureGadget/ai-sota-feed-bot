---
title: "LangSmith traces voice agents, including audio, STT/TTS latency, and interruptions"
date: 2026-07-21
theme: trace-capture
evidence: [dcbc4c8f98ebc760]
---
LangSmith now traces **voice agents** built on Pipecat, LiveKit, OpenAI Realtime, and Gemini Live, capturing audio, STT and TTS latency, interruptions, and tool calls in one trace.

Trajectory capture extends to the turn-taking and latency failures specific to spoken interfaces. See [agent latency](/topic/agent-latency) for why voice has a harder real-time floor.
