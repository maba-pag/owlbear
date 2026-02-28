---
id: 95
title: Create src/owlbear/voice/channel.py — VoiceChannel implementing ChannelPlugin
status: archived
priority: nice-to-have
created: 2026-02-27T03:08:02.1221995+01:00
updated: 2026-02-28T23:52:45.7641312+01:00
started: 2026-02-27T03:32:43.2290101+01:00
completed: 2026-02-28T23:52:45.7641312+01:00
tags:
    - phase-5
    - voice
    - agent
depends_on:
    - 92
    - 93
    - 94
class: standard
---

## Acceptance Criteria

- [ ] `VoiceChannel` class in `src/owlbear/voice/channel.py`
- [ ] Implements `ChannelPlugin` protocol from `owlbear.channels.base`
- [ ] `name` property returns `"voice"`
- [ ] `async send(message: str) -> None` delegates to `TTSEngine.speak(message)`
- [ ] `async receive(*, prompt: str | None = None) -> str | None` records audio via AudioRecorder, transcribes via STTEngine, returns text
- [ ] If `prompt` is provided, speaks it via TTS before recording
- [ ] Returns `None` if transcription is empty (silence / no speech detected)
- [ ] Constructor: `VoiceChannel(stt: STTEngine | None = None, tts: TTSEngine | None = None, recorder: AudioRecorder | None = None)` -- dependency injection for testability, creates defaults if None
- [ ] `isinstance(VoiceChannel(...), ChannelPlugin) == True` (runtime_checkable)
- [ ] Update `src/owlbear/voice/__init__.py` to export `VoiceChannel`
- [ ] Test file: `tests/test_voice_channel.py` -- mock all three components, verify protocol compliance, verify send delegates to speak, verify receive records then transcribes, verify prompt spoken before recording, verify None on empty transcription
- [ ] TDD: write tests first, then implement

Depends on: #92, #93, #94
See docs/voice-io-research.md section 3.5.
