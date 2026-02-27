---
id: 94
title: Create src/owlbear/voice/recorder.py — AudioRecorder wrapping PyAudio
status: todo
priority: low
created: 2026-02-27T03:07:54.6891889+01:00
updated: 2026-02-27T03:39:53.6924534+01:00
started: 2026-02-27T03:32:42.8220289+01:00
tags:
    - phase-5
    - voice
    - agent
depends_on:
    - 91
class: standard
---

## Acceptance Criteria

- [ ] `AudioRecorder` class in `src/owlbear/voice/recorder.py`
- [ ] Constructor: `AudioRecorder(sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024)`
- [ ] Method: `async record(duration: float) -> bytes` records audio for specified seconds, returns raw PCM bytes
- [ ] PyAudio stream open/read/close wrapped in `asyncio.to_thread()` to avoid blocking event loop
- [ ] Audio format: 16-bit signed integer (paInt16), matching faster-whisper expected input
- [ ] Guard import: `pyaudio` import wrapped in try/except with clear ImportError message ("Install with: uv sync --extra voice")
- [ ] Test file: `tests/test_voice_recorder.py` -- mock `pyaudio.PyAudio()`, verify stream params (rate, channels, format), verify duration calculation (chunks = rate * duration / chunk_size), verify bytes returned
- [ ] TDD: write tests first, then implement

Depends on: #91
See docs/voice-io-research.md section 3.4.

Note: `list_microphones()` deferred (YAGNI for push-to-talk MVP). Add when needed.
