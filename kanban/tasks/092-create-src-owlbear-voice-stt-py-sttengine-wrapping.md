---
id: 92
title: Create src/owlbear/voice/stt.py — STTEngine wrapping faster-whisper
status: archived
priority: nice-to-have
created: 2026-02-27T03:07:40.4602907+01:00
updated: 2026-02-28T23:52:44.3673363+01:00
started: 2026-02-27T03:32:42.0040256+01:00
completed: 2026-02-28T23:52:44.3673363+01:00
tags:
    - phase-5
    - voice
    - agent
depends_on:
    - 91
class: standard
---

## Acceptance Criteria

- [ ] `STTEngine` class in `src/owlbear/voice/stt.py`
- [ ] Constructor: `STTEngine(model_size: str = "base.en", compute_type: str = "int8", device: str = "cpu")`
- [ ] Method: `transcribe(audio: bytes, *, language: str = "en") -> str` returns transcribed text
- [ ] Lazy model loading: `faster_whisper.WhisperModel` created on first `transcribe()` call, not in `__init__`
- [ ] VAD filter enabled by default (Silero VAD via faster-whisper `vad_filter=True`)
- [ ] Guard import: `faster-whisper` import wrapped in try/except with clear ImportError message ("Install with: uv sync --extra voice")
- [ ] Test file: `tests/test_voice_stt.py` -- mock `faster_whisper.WhisperModel`, verify lazy loading, verify transcribe returns str, verify VAD param passed
- [ ] TDD: write tests first, then implement

Depends on: #91
See docs/voice-io-research.md sections 3.1-3.2.

Note: VoiceSettings removed from this task scope. Each component accepts config via constructor params. Unified settings integration deferred to #95 (VoiceChannel).
