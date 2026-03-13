---
id: 242
title: Rewrite STTEngine for Moonshine batch mode
status: archived
priority: needed
created: 2026-02-28T12:18:58.2452993+01:00
updated: 2026-02-28T23:54:20.9802863+01:00
started: 2026-02-28T16:34:33.3729767+01:00
completed: 2026-02-28T23:54:20.9802863+01:00
tags:
    - phase-10
    - voice
depends_on:
    - 241
class: standard
---

## Context
Rewrite STTEngine to use Moonshine batch mode (transcribe_without_streaming).

## Acceptance Criteria
- [ ] STTEngine wraps moonshine_voice.Transcriber (not faster-whisper)
- [ ] transcribe(audio: bytes, language='en') -> str API preserved
- [ ] Audio conversion: int16 PCM bytes -> float32 numpy array (/ 32768.0)
- [ ] Uses transcribe_without_streaming(audio_data, sample_rate=16000)
- [ ] Returns concatenated text from Transcript.lines
- [ ] Default model: ModelArch.SMALL_STREAMING (works in batch mode too)
- [ ] Model path resolved via moonshine_voice.get_model_for_language()
- [ ] Lazy model loading preserved (Transcriber created on first transcribe call)
- [ ] close() releases Transcriber native resources (ONNX Runtime); safe to call when model not loaded
- [ ] ImportError with helpful message when moonshine-voice not installed
- [ ] All existing STT tests updated + passing
- [ ] TDD: write failing tests first

## Design Reference
See docs/research/moonshine-streaming.md S3.2 for audio format, S4.1 for two-mode arch, S4.3 for class design.
