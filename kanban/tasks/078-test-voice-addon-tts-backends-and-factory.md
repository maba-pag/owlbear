---
id: 78
title: 'Test: voice addon TTS backends and factory'
status: backlog
priority: nice-to-have
created: 2026-03-26T21:17:56.9640853+01:00
updated: 2026-03-26T21:17:56.9640853+01:00
tags:
    - phase-3
    - scope:voice
    - test
depends_on:
    - 52
class: standard
---

## Objective
RED phase tests for #51 TTS backends.

## Acceptance Criteria
- [ ] Test TTSBackend protocol compliance for both backends
- [ ] Test KokoroTTSBackend.speak() with mocked KPipeline and sounddevice
- [ ] Test Pyttsx3TTSBackend.speak() with mocked pyttsx3.init()
- [ ] Test create_tts_backend() returns Kokoro when available
- [ ] Test create_tts_backend() falls back to pyttsx3 when kokoro import fails
- [ ] Test create_tts_backend() falls back on Kokoro init error (espeak-ng missing)
- [ ] Test speed mapping: 1.0 maps to Kokoro speed=1.0 and pyttsx3 rate=200
- [ ] Test voice config passed through to each backend
- [ ] All tests fail (RED phase)

## Context
Test task for #51. See docs/research/voice-tts-kokoro-pyttsx3.md for API details.
