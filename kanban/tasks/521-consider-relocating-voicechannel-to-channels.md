---
id: 521
title: Consider relocating VoiceChannel to channels/ package
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:30.0955145+01:00
updated: 2026-03-04T07:38:30.0955145+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

ARC-03: All channel adapters (CLI, Slack) live under channels/ except VoiceChannel under voice/. voice/ conflates I/O abstraction with voice processing. Option: move VoiceChannel to channels/voice.py (importing STT/TTS from voice/). AC: design decision documented. See docs/architecture-audit.md.
