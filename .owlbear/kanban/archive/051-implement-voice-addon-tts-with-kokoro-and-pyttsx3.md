---
id: 51
title: Implement voice addon TTS with Kokoro and pyttsx3 fallback
status: archived
priority: medium
created: 2026-03-26 18:57:30.584841+01:00
updated: 2026-03-30 06:33:38.942444+02:00
started: 2026-03-30 06:33:11.833946+02:00
completed: 2026-03-30 06:33:11.833946+02:00
tags:
- phase-3
- scope:voice
depends_on:
- 52
- 78
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Build the TTS subsystem for the voice addon: a TTSBackend protocol, Kokoro primary backend, pyttsx3 fallback backend, and a factory function that selects the backend at import time.

## Acceptance Criteria

- [ ] TTSBackend protocol in owlbear_voice/tts/protocol.py: speak(text: str) -> None (blocking), close() -> None
- [ ] KokoroTTSBackend in owlbear_voice/tts/kokoro_backend.py: calls KPipeline(lang_code) lazily on first speak(); iterates generator yielding Result; plays each chunk via sounddevice.play(result.audio.numpy(), 24000) then sd.wait()
- [ ] Pyttsx3TTSBackend in owlbear_voice/tts/pyttsx3_backend.py: lazy pyttsx3.init() on first speak(); calls engine.say(text) + engine.runAndWait(); mirrors v1 TTSEngine lazy-init pattern
- [ ] Import-time fallback flag: _kokoro_available set via try/import kokoro at module top of factory module; no runtime detection per call
- [ ] create_tts_backend(voice: str, speed: float) factory in owlbear_voice/tts/__init__.py: returns KokoroTTSBackend when available, else Pyttsx3TTSBackend; logs which backend was selected
- [ ] Speed mapping: normalized float (1.0 = normal) mapped to Kokoro speed param directly and pyttsx3 rate as int(speed * 200)
- [ ] Voice mapping: string passed to Kokoro as voice param; for pyttsx3, used as substring match against engine.getProperty('voices') IDs
- [ ] Kokoro init failure (espeak-ng missing, model download failure) caught and falls back to pyttsx3 with warning log; factory never raises on backend selection
- [ ] Unit tests with mocked kokoro.KPipeline, pyttsx3.init(), and sounddevice.play(); tests cover: both backends speak, factory fallback when kokoro unavailable, factory fallback on Kokoro init error, speed/voice config mapping

## Dependencies

Depends on #52 (owlbear-voice workspace package scaffold)

## Context

See docs/research/voice-tts-kokoro-pyttsx3.md for API details.
See docs/research/voice-addon-architecture.md for architecture decision.
Port lazy-init pattern from v1/src/owlbear/voice/tts.py.

[[2026-03-26]] Thu 21:19

## Architecture Review

Verdict: REFINE

### AC Assessment

Original AC line: Kokoro TTS generate audio from text, play via sounddevice
Assessment: Vague, no interface specified
Action: Rewritten with TTSBackend protocol, KokoroTTSBackend class, specific KPipeline API calls, sounddevice.play() at 24kHz

Original AC line: pyttsx3 fallback when torch/kokoro not installed
Assessment: Missing detection mechanism and interface
Action: Rewritten with import-time flag, Pyttsx3TTSBackend class, lazy init pattern from v1

Original AC line: Reads speak commands from stdin JSON
Assessment: Belongs to stdio protocol task #49, not TTS module (single responsibility violation)
Action: Removed from AC

Original AC line: Configurable voice and speed
Assessment: Missing config type and mapping details
Action: Rewritten with normalized float speed mapping and voice string passthrough per backend

Original AC line: Unit tests with mocked dependencies
Assessment: Missing specifics
Action: Rewritten with explicit mock targets and test scenarios

### Architecture Notes

TTS backends are a leaf module in the owlbear-voice package with no upward dependencies.
TTSBackend protocol follows typing.Protocol pattern per architecture standards.
Factory function with import-time detection is KISS-aligned (validated by v1 pattern in v1/src/owlbear/voice/tts.py).
Kokoro init failure gracefully falls back rather than raising, since this is a non-critical subsystem.
Module path: owlbear_voice/tts/ (protocol.py, kokoro_backend.py, pyttsx3_backend.py, __init__.py with factory).

### Changes Made

Rewrote AC body with 9 precise, testable criteria
Removed stdin JSON reading (belongs to #49 stdio protocol)
Added depends_on #52 (workspace package scaffold)
Added depends_on #78 (test task, TDD compliance)
Created #78: Test voice addon TTS backends and factory (RED phase)

### Dependencies

Added: #52 (owlbear-voice workspace package scaffold)
Added: #78 (test task, TDD RED phase)
Verified: #49 (stdio protocol) is a sibling, not a dependency for this task

[[2026-03-29]] Sun 15:38
## Architecture Review (Pass 2)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| TTSBackend protocol speak()+close() | Precise, file path specified, methods typed | No change |
| KokoroTTSBackend lazy KPipeline + sounddevice | Specific API calls, sample rate, chunk iteration | No change |
| Pyttsx3TTSBackend lazy init + say/runAndWait | Mirrors v1 pattern, file path specified | No change |
| Import-time _kokoro_available flag | Detection mechanism clear, no per-call overhead | No change |
| create_tts_backend factory in __init__.py | Params typed, return logic clear, logging required | No change |
| Speed mapping 1.0 normal | Concrete formula for both backends | No change |
| Voice mapping string passthrough/substring | Clear per-backend behavior | No change |
| Kokoro init failure fallback | Error types listed, factory never-raise contract | No change |
| Unit tests with mocked deps | Specific mocks and scenarios enumerated | No change |

### Architecture Notes
- All 9 AC lines from prior REFINE pass are precise and mechanically verifiable.
- Protocol pattern: typing.Protocol matches owlbear_knowledge/protocol.py and embeddings.py patterns.
- close() method not in v1 but appropriate for v2 resource cleanup (Kokoro torch memory).
- Module path owlbear_voice/tts/ is a leaf subpackage with no upward deps. Verified packages/voice/src/owlbear_voice/ currently has only stubs.
- Import-time fallback validated against v1 pattern (v1/src/owlbear/voice/tts.py uses identical try/import/except).
- Single domain: scope:voice (TTS subsystem only). No cross-domain concerns.
- No new security surface: audio playback is local, no user input parsing (stdin belongs to #49).
- Factory never-raise contract is appropriate for a non-critical addon subsystem.

### Dependencies
- Verified: #52 (owlbear-voice workspace package) archived
- Verified: #78 (TDD RED test task) exists at backlog, depends on #52 (satisfied)
- TDD sequencing: #51 depends_on #78 ensures RED before GREEN

### Changes Made
- Approved task, moved to todo

[[2026-03-29]] Sun 20:26
## Builder Notes
- Files changed: packages/voice/src/owlbear_voice/tts/__init__.py, kokoro_backend.py, protocol.py, pyttsx3_backend.py
- Tests: 40 passed (all TestFromAC_* green), 0 failures
- Coverage: tts/__init__.py 100%, kokoro_backend.py 93%, protocol.py 100%, pyttsx3_backend.py 97%
- Lint: ruff check -- all checks passed
- Evidence: uv run pytest tests/test_voice_tts.py -- 40 passed in 53.95s
- Fixes applied: Rewrote kokoro_backend.py to use module-level try/except import of KPipeline (ruff PLC0415 compliance); used object type instead of Any (ruff ANN401 compliance)

[[2026-03-30]] Mon 05:24
## Review Evidence
See docs/scratch/51-reviewer.md for full evidence.

[[2026-03-30]] Mon 06:33
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 5ca9937 | chore | kanban/tasks/051-*.md | #51 |
