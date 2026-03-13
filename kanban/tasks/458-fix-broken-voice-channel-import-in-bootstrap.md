---
id: 458
title: Fix broken voice channel import in bootstrap
status: archived
priority: critical
created: 2026-03-04T07:37:38.3966046+01:00
updated: 2026-03-06T19:28:06.1813483+01:00
started: 2026-03-06T00:04:18.5270232+01:00
completed: 2026-03-06T19:28:06.1813483+01:00
tags:
    - audit
    - bugfix
    - scope:core
class: standard
---

Research complete (docs/research/voice-channel-import.md).

Fix: change bootstrap.py L241 from `from owlbear.channels.voice import VoiceChannel` to `from owlbear.voice import VoiceChannel`.

Do NOT relocate VoiceChannel to channels/ -- it belongs with the voice/ subsystem (STT, TTS, streaming_stt are tightly coupled). Relocating violates KISS/YAGNI.

AC:
- [ ] bootstrap.py import changed to `from owlbear.voice import VoiceChannel`
- [ ] voice channel starts without ImportError
- [ ] existing tests pass
- [ ] ruff clean
