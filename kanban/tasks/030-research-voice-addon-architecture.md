---
id: 30
title: Research voice addon architecture
status: ideation
priority: nice-to-have
created: 2026-03-26T18:05:24.8333451+01:00
updated: 2026-03-26T18:05:24.8333451+01:00
tags:
    - phase-3
    - scope:voice
    - research
class: standard
---

## Objective
Design the voice component as a standalone addon that integrates with owlbear without being tightly coupled.

## Acceptance Criteria
- [ ] Research current local voice models (Whisper variants, Moonshine, etc.)
- [ ] Decide: standalone app started by owlbear vs independent process
- [ ] Design the interface between voice and owlbear (pipes, MCP server, or API)
- [ ] Evaluate if integration is simple enough to be worth it vs staying fully standalone
- [ ] Assess resource usage (local model on laptop - memory, CPU, battery)
- [ ] Write findings to docs/research/voice-addon-architecture.md
- [ ] Create follow-up tasks

## Context
v1 had voice as an integrated module (Whisper STT + pyttsx3 TTS). v2 treats voice as a separate system. This task explores whether a lightweight integration makes sense (e.g., owlbear spawns the voice process, voice feeds prompts to owlbear) vs fully standalone.
