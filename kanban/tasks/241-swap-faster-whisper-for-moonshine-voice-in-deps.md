---
id: 241
title: Swap faster-whisper for moonshine-voice in deps
status: archived
priority: needed
created: 2026-02-28T12:18:45.7181963+01:00
updated: 2026-02-28T23:54:20.2572424+01:00
started: 2026-02-28T16:34:32.7838739+01:00
completed: 2026-02-28T23:54:20.2572424+01:00
tags:
    - phase-10
    - voice
class: standard
---

## Context
Replace faster-whisper with moonshine-voice in pyproject.toml [voice] extras.

## Acceptance Criteria
- [ ] pyproject.toml [voice] group: moonshine-voice>=0.0.49,<0.1.0 replaces faster-whisper
- [ ] pyaudio removed from [voice] group (sounddevice is a moonshine-voice transitive dep)
- [ ] numpy added explicitly to [voice] group
- [ ] pyttsx3 remains (TTS unchanged)
- [ ] uv sync --extra voice installs moonshine-voice + sounddevice + numpy successfully
- [ ] No import errors on import owlbear.voice

## Notes
- moonshine-voice v0.0.49, MIT license, ONNX Runtime core
- sounddevice replaces pyaudio for mic capture (pulled in by moonshine-voice)
- See docs/moonshine-streaming-research.md S4.2
