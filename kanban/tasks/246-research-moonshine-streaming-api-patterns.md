---
id: 246
title: Research Moonshine streaming API patterns
status: archived
priority: needed
created: 2026-02-28T12:19:43.4347411+01:00
updated: 2026-02-28T23:54:24.1793074+01:00
started: 2026-02-28T13:57:47.8032225+01:00
completed: 2026-02-28T23:54:24.1793074+01:00
tags:
    - phase-10
    - voice
    - research
class: standard
---

## Context
The Moonshine research (#240) covered viability and comparison but did not deep-dive into the streaming API internals. Before implementing #243, we need to understand: Transcriber lifecycle, event callbacks (on_text, on_segment, etc.), audio format requirements for add_audio(), MicTranscriber vs manual audio feeding, session management, and error handling.

## Acceptance Criteria
- [ ] Research checklist completed (see copilot-instructions.md)
- [ ] Document Transcriber event-driven API: start/stop/add_audio/listeners
- [ ] Document MicTranscriber: does it handle mic I/O internally?
- [ ] Document audio chunk format and size requirements for add_audio()
- [ ] Document session management: how to handle pauses between speech segments
- [ ] Document error handling: what happens on bad audio, timeout, etc.
- [ ] Identify gaps between Moonshine API and our brainstorming use case
- [ ] Follow-up kanban tasks created from findings

## Notes
- Clone moonshine-ai/moonshine to docs/research/ for analysis
- Focus on Python API in moonshine_voice package
- Test with Small Streaming model (123M)
- This gates #243 implementation
