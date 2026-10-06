---
title: "Make0 builds plug-and-play memory so Codex and Claude Code share context"
date: 2026-09-18
theme: shared-memory
evidence: [17de01e9c2b4e169]
---
**Make0 AI** is a personal memory layer meant to give Codex and Claude Code common context. The pain point is concrete: after hitting one agent's usage limit, switching tools means starting from scratch.

The author's first attempt, a shared Markdown instruction file, kept growing until the common context **passed 20k tokens**. A shared file without curation hits the same unbounded-growth problem as `CLAUDE.md`.
