---
id: 50
title: Implement voice addon STT with Moonshine
status: in-progress
priority: nice-to-have
created: 2026-03-26T18:57:23.8838546+01:00
updated: 2026-03-31T07:30:14.975871+02:00
tags:
    - phase-3
    - scope:voice
depends_on:
    - 52
    - 61
class: standard
---

## Objective
Build the STT component of the voice addon using moonshine-voice. This module lives in the owlbear-voice package and wraps MicTranscriber for streaming speech-to-text with VAD, outputting transcript events as NDJSON on stdout.

## Acceptance Criteria
- [ ] SttRunner class in owlbear_voice/stt.py with start(), stop(), close() lifecycle methods
- [ ] SttRunner lazily creates MicTranscriber on first start() call (not at __init__); port pattern from v1 StreamingSTT._create_mic_transcriber()
- [ ] SttRunner constructor accepts keyword params: model_arch (default ModelArch.SMALL_STREAMING), language (default en), update_interval (default 0.5)
- [ ] TranscriptJsonListener subclasses moonshine_voice.TranscriptEventListener; implements on_line_started, on_text_changed, on_line_completed, on_error
- [ ] TranscriptJsonListener serializes events to NDJSON on stdout using VoiceOutMessage models (transcript, partial, error types from task #61)
- [ ] Thread-safe stdout writes: threading.Lock guards sys.stdout.buffer.write() + flush() since Moonshine callbacks fire on the sounddevice audio thread
- [ ] on_error emits error-type NDJSON message to stdout and logs detail to stderr
- [ ] Emits status-type message with state ready after successful MicTranscriber creation
- [ ] stop() calls MicTranscriber.stop() which triggers LineCompleted for any active line
- [ ] close() releases MicTranscriber resources; idempotent (safe to call before start or multiple times)
- [ ] Raises ImportError with actionable install message when moonshine-voice is not installed (guarded import in method, not module top)
- [ ] Unit tests mock moonshine_voice.MicTranscriber, TranscriptEventListener, get_model_for_language, ModelArch; test scenarios: lazy creation on first start(), start/stop lifecycle state transitions, JSON output for all 3 event types, thread safety with concurrent callback simulation, close idempotency, ImportError when missing

## Dependencies
Depends on #52 (owlbear-voice package scaffold) and #61 (voice protocol Pydantic models for message types).

## Context
See docs/research/voice-addon-stt-moonshine.md for Moonshine API details, thread safety analysis, and JSON message format.
See docs/research/voice-addon-architecture.md for architecture decision (standalone process, stdio pipes).
Port lazy-init pattern from v1/src/owlbear/voice/streaming_stt.py.

[[2026-03-27]] Fri 02:52
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| MicTranscriber-based streaming STT with VAD | Vague: no class name, module path, or lifecycle API | Rewritten with SttRunner class, owlbear_voice/stt.py, start/stop/close |
| Outputs transcript lines as JSON on stdout | Missing: JSON schema, thread safety, event types | Rewritten with TranscriptJsonListener, NDJSON format per #61 models, threading.Lock |
| Configurable model arch and language | Missing: defaults, param types, where configured | Rewritten with keyword params and defaults (SMALL_STREAMING, en, 0.5) |
| Lazy model loading on first activation | Adequate concept, no code reference | Refined: port v1 StreamingSTT._create_mic_transcriber() pattern |
| Unit tests with mocked moonshine-voice | Vague: no mock targets or scenarios | Rewritten with specific mock targets and 6 test scenarios |

### Architecture Notes
STT is a leaf module in the owlbear-voice package with no upward dependencies. Follows the standalone process architecture from #30 research. TranscriptJsonListener pattern matches the Moonshine Ollama voice example (TranscriptEventListener subclass). Thread safety via threading.Lock is validated by research as adequate at Moonshine event frequencies (2-4/sec). Protocol models from #61 ensure message format consistency between STT output and the owlbear-side process manager (#62).

Implicit blocker chain: #50 requires #52 (package scaffold) requires #7 (monorepo skeleton, ideation). Voice work cannot start until the v2 directory structure exists.

### Changes Made
- Rewrote AC with 12 precise, testable lines
- Added depends_on: #52, #61
- Updated Context section with both research doc references

### Dependencies
- Added: #52 (owlbear-voice package scaffold)
- Added: #61 (voice protocol Pydantic models)
- Verified implicit chain: #52 requires #7 (monorepo skeleton, ideation)

[[2026-03-30]] Mon 18:12
## Test-Writer Notes
- Test file: tests/test_voice_stt.py
- Classes: TestFromAC_SttRunnerClass, TestFromAC_LazyMicTranscriberCreation, TestFromAC_SttRunnerConstructorParams, TestFromAC_TranscriptJsonListenerStructure, TestFromAC_NdjsonOutput, TestFromAC_ThreadSafeStdout, TestFromAC_OnErrorLogsToStderr, TestFromAC_StatusReadyMessage, TestFromAC_StopDelegatesToMicTranscriber, TestFromAC_CloseIdempotency, TestFromAC_ImportErrorWhenMissingMoonshine
- Tests per category: happy 14, edge 8, error 7, boundary 7
- Total: 36 tests, 36 PASS (pre-existing implementation)
- ruff: clean
- Note: stt.py was pre-implemented prior to RED phase. Test file existed from prior incomplete pass with 2 broken tests in TestFromAC_ThreadSafeStdout (monkeypatching sys.stdout.buffer which is readonly under pytest). Fixed to use patch.object on owlbear_voice.stt.sys binding, matching captured_stdout fixture approach.
- AC coverage: all 11 AC lines covered (AC1-SttRunner lifecycle, AC2-lazy init, AC3-constructor kwargs, AC4-TranscriptJsonListener MRO, AC5-NDJSON types, AC6-thread safety, AC7-stderr logging, AC8-status ready, AC9-stop delegation, AC10-close idempotency, AC11-ImportError guard)

[[2026-03-31]] Tue 07:30
## Test-Writer Notes (resume 2026-03-31)
- Prior session (2026-03-30) completed all RED-phase work but did not advance the task.
- test_voice_stt.py is committed at 7800236; ruff clean; 36 tests PASS against pre-existing implementation.
- Advancing to in-progress now.
