---
id: 243
title: Implement streaming STT for brainstorming sessions
status: archived
priority: needed
created: 2026-02-28T12:19:10.4938359+01:00
updated: 2026-02-28T23:54:21.7108542+01:00
started: 2026-02-28T16:34:33.8996293+01:00
completed: 2026-02-28T23:54:21.7108542+01:00
tags:
    - phase-10
    - voice
depends_on:
    - 242
    - 246
class: standard
---

## Context
Implement Moonshine streaming STT using MicTranscriber for brainstorming sessions.

## Acceptance Criteria
- [ ] New StreamingSTT class in src/owlbear/voice/streaming_stt.py
- [ ] Uses MicTranscriber(model_path, model_arch=SMALL_STREAMING, update_interval=0.5)
- [ ] start() begins mic capture + streaming transcription
- [ ] stop() returns full transcript as str, calls MicTranscriber.stop()
- [ ] on_text_update callback fires on LineTextChanged events
- [ ] on_line_complete callback fires on LineCompleted events
- [ ] Thread safety: callbacks queued to asyncio event loop (sounddevice fires on audio thread)
- [ ] close() releases MicTranscriber + Transcriber resources
- [ ] Configurable model_arch (default SMALL_STREAMING) and update_interval (default 0.5s)
- [ ] All tests mock the moonshine_voice C library layer
- [ ] TDD: write failing tests first

See docs/moonshine-streaming-research.md S4.3 for class design.
