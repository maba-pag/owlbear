---
id: 93
title: Create src/owlbear/voice/tts.py — TTSEngine wrapping pyttsx3
status: todo
priority: low
created: 2026-02-27T03:07:47.5747552+01:00
updated: 2026-02-27T03:39:53.6860214+01:00
started: 2026-02-27T03:32:42.4165989+01:00
tags:
    - phase-5
    - voice
    - agent
depends_on:
    - 91
class: standard
---

## Acceptance Criteria

- [ ] `TTSEngine` class in `src/owlbear/voice/tts.py`
- [ ] Constructor: `TTSEngine(rate: int = 200, volume: float = 1.0)`
- [ ] Method: `async speak(text: str) -> None` speaks text via pyttsx3
- [ ] pyttsx3 `engine.say()` + `engine.runAndWait()` wrapped in `asyncio.to_thread()` to avoid blocking event loop
- [ ] Lazy engine init: pyttsx3 engine created on first `speak()` call, not in `__init__`
- [ ] Guard import: `pyttsx3` import wrapped in try/except with clear ImportError message ("Install with: uv sync --extra voice")
- [ ] Test file: `tests/test_voice_tts.py` -- mock `pyttsx3.init()`, verify speak calls engine.say + runAndWait, verify async wrapping via to_thread, verify rate/volume applied
- [ ] TDD: write tests first, then implement

Depends on: #91
See docs/voice-io-research.md section 3.3.
