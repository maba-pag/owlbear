---
id: 244
title: Refactor VoiceChannel for brainstorming mode
status: archived
priority: needed
created: 2026-02-28T12:19:21.2312355+01:00
updated: 2026-02-28T23:54:22.5084695+01:00
started: 2026-02-28T16:34:34.5108692+01:00
completed: 2026-02-28T23:54:22.5084695+01:00
tags:
    - phase-10
    - voice
depends_on:
    - 243
class: standard
---

## Context
Refactor VoiceChannel.receive() to support brainstorming mode. Two modes: quick (existing push-to-record) and brainstorm (open-ended streaming session). Moonshine's MicTranscriber handles mic + VAD + streaming internally for brainstorm mode.

## Acceptance Criteria
- [ ] VoiceChannel exposes brainstorm(duration: float = 120, on_update: Callable | None = None) -> str
- [ ] Quick mode (receive): unchanged API, uses sounddevice for mic capture (replaces pyaudio/AudioRecorder usage), passes PCM to STTEngine.transcribe()
- [ ] Brainstorm mode: delegates to StreamingSTT.start/stop, accumulates full transcript
- [ ] on_update callback receives partial text on each LineTextChanged event
- [ ] Session ends on: manual stop, duration timeout, or session-level silence timeout (no speech detected for configurable idle_timeout, default 10s)
- [ ] Session-level silence is distinct from VAD segment pauses — VAD segments speech; idle_timeout ends the whole session
- [ ] Full transcript (all completed lines joined) returned at session end
- [ ] ChannelPlugin protocol still satisfied (receive returns str | None)
- [ ] CLI: bearclaw voice brainstorm [--duration 120] [--idle-timeout 10] added
- [ ] TDD: write failing tests first

## Architecture Notes
- quick mode mic capture: sounddevice.rec(frames, samplerate=16000, channels=1, dtype='int16') -> numpy -> bytes -> STTEngine.transcribe()
- brainstorm mode: StreamingSTT (from #243) handles everything
- AudioRecorder becomes unused after this task (removal deferred to #245)
- VAD auto-segments at pauses (max 15s segments); idle_timeout is a separate higher-level timer

## Design Reference
See docs/moonshine-streaming-research.md S4.1 and S4.3.
