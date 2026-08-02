---
id: 50
title: Implement voice addon STT with Moonshine
status: archived
priority: medium
created: 2026-03-26 18:57:23.883855+01:00
updated: 2026-04-01 17:57:36.100602+02:00
started: 2026-04-01 17:57:26.243473+02:00
completed: 2026-04-01 17:57:26.243473+02:00
tags:
- phase-3
- scope:voice
depends_on:
- 52
- 61
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-31]] Tue 23:58
Builder Notes: 36 passed, coverage 94%, ruff clean

[[2026-04-01]] Wed 02:42
## Review Evidence
See docs/scratch/50-reviewer.md for full evidence.

[[2026-04-01]] Wed 03:42
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited Step 6.5 implementation-aware gaps (missing tests, not code quality)
- Added: 6 new tests for on_line_started (3) and on_line_text_changed bridge (3)
- Classes: TestFromAC_OnLineStartedEmission, TestFromAC_OnLineTextChangedBridge
- Preserved: 36 original tests (all PASS)
- New tests: all PASS (implementation pre-existed from builder GREEN phase -- same situation as original 36)
- ruff: clean
- Coverage addressed: on_line_started body (stt.py line 54), on_line_text_changed bridge (line 78)
- Total now: 42 tests, ruff clean

[[2026-04-01]] Wed 14:42
## Builder Notes (retry)\n- 42 passed, ruff clean, 97% on stt.py\n- No code changes: test-writer retry tests pass against pre-existing implementation

[[2026-04-01]] Wed 15:43
## Review Evidence (retry 2026-04-01)
See docs/scratch/50-reviewer.md for cycle-1 evidence.

### Retry Scope
Prior FAIL reasons:
1. on_line_started body (stt.py line 54) - never invoked in any test
2. on_line_text_changed bridge (stt.py line 78) - builder-added production path, zero coverage

### Test Results
- pytest: 42 passed, 0 failed (was 36)
- New classes: TestFromAC_OnLineStartedEmission (3), TestFromAC_OnLineTextChangedBridge (3)

### Lint Results
- ruff: All checks passed!

### Coverage
- stt.py: 97% (lines 20-21 only - ImportError fallback, moonshine_voice IS installed, acceptable)
- Lines 54 and 78 are now covered (confirmed by delta from 94% to 97%)

### Retry Gap Resolution

| Prior Finding | Fix | Adequate? |
|---|---|---|
| line 54 on_line_started body untested | TestFromAC_OnLineStartedEmission 3 tests: type partial, text empty string, line_idx forwarded | YES - specific assertions would catch wrong field names or values |
| line 78 on_line_text_changed bridge untested | TestFromAC_OnLineTextChangedBridge 3 tests: type partial, event.line.text forwarded, event.line.line_id forwarded | YES - mock event with specific attribute names, exact value checks |

### Test Quality (new tests)
Assertion specificity - STRONG: each test checks exact field values (type, text, line_idx)
Mutation robustness: if event.line.line_id were renamed or wrong, test_on_line_text_changed_forwards_event_line_id would FAIL
Test independence - STRONG: each test creates its own listener and captured_stdout fixture

### TestFromAC Integrity
- 11 original TestFromAC_ classes: PRESERVED (36 tests, all pass)
- 2 new TestFromAC_ classes added by test-writer retry (correctly mapped to AC4/AC5)
- No weakened or removed assertions

### AC Compliance
All 11 AC lines: PASS (unchanged from cycle-1 evidence in docs/scratch/50-reviewer.md)
AC5 LAX finding resolved: on_line_started emission and on_line_text_changed bridge both now tested

### Verdict: PASS
Confidence: .93

[[2026-04-01]] Wed 16:16
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | packages/voice/ already listed as speech recognition + TTS; no convention change |
| 2 | Docstrings | Yes | Pass | All public classes/methods in stt.py have docstrings: TranscriptJsonListener, SttRunner, emit, on_line_started, on_text_changed, on_line_completed, on_error, on_line_text_changed, start, stop, close, _create_transcriber |
| 3 | docs/sources/overview.md | Yes | Pass | Section Voice Addon STT with Moonshine (Task #50) already present with 3 Moonshine source entries |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research docs | Yes | Pass | docs/research/voice-addon-stt-moonshine.md and docs/research/voice-addon-architecture.md both exist and linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/50-reviewer.md (deleted)

[[2026-04-01]] Wed 17:57
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 SttRunner class lifecycle | stt.py L91 class, L117 start, L148 stop, L159 close | PASS |
| AC2 Lazy MicTranscriber | stt.py L119 guard: if _transcriber is None | PASS |
| AC3 Constructor kwargs defaults | stt.py L104 model_arch=None, language=en, update_interval=0.5 | PASS |
| AC4 TranscriptJsonListener subclass | stt.py L30 inherits TranscriptEventListener | PASS |
| AC5 NDJSON serialization | stt.py L44 _write with json.dumps, 3 event types | PASS |
| AC6 Thread-safe writes | stt.py L46 Lock guards write+flush | PASS |
| AC7 on_error stderr+NDJSON | stt.py L71 stderr.write + error-type message | PASS |
| AC8 Status ready message | stt.py L120 emit status/ready after creation | PASS |
| AC9 stop delegates | stt.py L155 _transcriber.stop() | PASS |
| AC10 close idempotent | stt.py L159 None check, sets None after close | PASS |
| AC11 ImportError guard | stt.py L129 guarded import, actionable message | PASS |

### Test Results
- pytest: 42 passed, 0 failed (test_voice_stt.py)
- Full suite: 222 failures, none in task scope
- ruff: All checks passed

### AC Quality: 5/5
12 precise testable lines; architect refined from vague originals into specific class names, method signatures, mock targets.

### Deduction breakdown: none (all 11 AC verified with file+line evidence, lint clean, tests pass, reviewer evidence thorough)
### Confidence: 1.0
### Action: archive
