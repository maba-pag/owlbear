---
id: 746
title: 'P1-01: Archive voice I/O research docs to handoff location'
status: todo
priority: needed
created: '2026-04-10T10:36:20.117217+00:00'
updated: '2026-04-10T10:36:20.117217+00:00'
tags:
- phase-1
- type:archive
- cleanup
- scope-reduction
parent: 745
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — straightforward file move.

Voice research docs are valuable to the future dictation project. Archive them under the existing handoff brief before the deletion pass removes the originals.

## Acceptance Criteria
1. All 11 voice I/O research docs copied to `.owlbear/briefs/draft-voice-rethink/research-archive/`:
   - `voice-addon-architecture.md`, `voice-addon-stt-moonshine.md`, `voice-channel-import.md`, `voice-io.md`, `voice-panel-handbook.md`, `voice-process-manager.md`, `voice-protocol-models.md`, `voice-stdio-protocol.md`, `voice-tts-kokoro-pyttsx3.md`, `moonshine-streaming.md`, `moonshine-vs-whisper.md`
2. Originals deleted from `.owlbear/research/`
3. Handoff doc `.owlbear/briefs/draft-voice-rethink/handoff-dictation-project.md` updated with archive manifest listing all moved files

## CRITICAL
Do NOT touch `voice-panel-handbook.md` in `share/skills/` — that is the ideation voice panel, NOT voice I/O. Only the `.owlbear/research/voice-panel-handbook.md` copy is in scope.

## Files
- Source: `.owlbear/research/voice-*.md`, `.owlbear/research/moonshine-*.md`
- Target: `.owlbear/briefs/draft-voice-rethink/research-archive/`
- Edit: `.owlbear/briefs/draft-voice-rethink/handoff-dictation-project.md`
