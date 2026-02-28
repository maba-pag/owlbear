---
id: 245
title: Remove all faster-whisper references and clean up
status: archived
priority: needed
created: 2026-02-28T12:19:30.9173342+01:00
updated: 2026-02-28T23:54:23.4535902+01:00
started: 2026-02-28T16:34:35.0936615+01:00
completed: 2026-02-28T23:54:23.4535902+01:00
tags:
    - phase-10
    - voice
depends_on:
    - 244
class: standard
---

## Context
Clean sweep: remove all traces of faster-whisper AND pyaudio from the codebase. This is the final task in the Moonshine migration chain — runs after all functional migration is complete.

## Acceptance Criteria
- [ ] No import of faster_whisper anywhere in src/ or tests/
- [ ] No import of pyaudio anywhere in src/ or tests/
- [ ] No mention of faster-whisper or pyaudio in pyproject.toml
- [ ] No mention of faster-whisper in docs (except research docs which are historical)
- [ ] No mention of whisper in code comments (except research context)
- [ ] AudioRecorder class removed (no consumers remain after #244 replaced its usage with sounddevice)
- [ ] test_voice_recorder.py deleted along with AudioRecorder
- [ ] All voice tests pass without faster-whisper or pyaudio installed
- [ ] ruff check clean
- [ ] grep -r verification: zero hits for faster.whisper, pyaudio, faster_whisper in src/ and tests/

## Notes
- pyaudio fully replaced by sounddevice (Moonshine transitive dep, used via MicTranscriber in brainstorm mode and directly in quick mode)
- AudioRecorder has no consumers after #244; safe to delete
- bootstrap.py has a pre-existing bug: imports from owlbear.channels.voice (does not exist) — out of scope but worth noting
