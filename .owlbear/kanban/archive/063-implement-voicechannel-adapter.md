---
id: 63
title: Implement VoiceChannel adapter
status: archived
priority: medium
created: 2026-03-26 19:33:48.974337+01:00
updated: 2026-04-06 06:23:54.278943+02:00
started: 2026-04-06 06:23:54.278943+02:00
completed: 2026-04-06 06:23:54.278943+02:00
tags:
- phase-3
- scope:voice
depends_on:
- 61
- 62
- 142
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Build the ChannelPlugin adapter that wraps the voice process manager.

## Acceptance Criteria

### Public API contract
- [ ] Class `VoiceChannel` with async context manager (`__aenter__` / `__aexit__`)
- [ ] `__init__(manager: VoiceProcessManager)` constructor injection (no default)
- [ ] `name` property returns `"voice"` (str)
- [ ] `async send(message: str) -> None`
- [ ] `async receive(*, prompt: str | None = None) -> str | None`

### send() behavior
- [ ] Creates `SpeakMsg(type="speak", text=message, interrupt=False)` and delegates to `await manager.send(msg)`

### receive() behavior
- [ ] If `prompt` is provided, calls `await self.send(prompt)` before listening
- [ ] Lazy start: on first call, enters process manager context (`await manager.__aenter__()`) if not yet started; tracks with `_started: bool` flag
- [ ] Loops `await manager.receive()`, skipping messages that are not `TranscriptMsg` with `final=True`
- [ ] Returns `TranscriptMsg.text` on match
- [ ] Returns `None` if `VoiceProcessError` is raised (process unrecoverably dead)

### Lifecycle
- [ ] `__aenter__` returns `self` (no-op, lazy start deferred to receive)
- [ ] `__aexit__` calls `await manager.shutdown()` if `_started` is True; no-op otherwise

### Rich methods (ChannelPlugin defaults)
- [ ] `async send_file(path, *, caption=None)` sends `f"[{caption}] {path}"` or `str(path)` via `send()`
- [ ] `async send_blocks(blocks, text_fallback)` sends `text_fallback` via `send()`
- [ ] `async send_image(file_or_bytes, *, caption=None)` sends `caption or "[image]"` via `send()`

### Module location
- [ ] `packages/orchestrator/src/owlbear/voice/channel.py`

### Patterns to follow
- Constructor DI (v1/src/owlbear/voice/channel.py pattern)
- Import from `owlbear.voice.protocol`: SpeakMsg, TranscriptMsg
- Import from `owlbear.voice.process`: VoiceProcessManager, VoiceProcessError
- No brainstorm/partial handling (YAGNI)

## Test task
#142 (todo) tests at tests/test_voice_channel.py

## Context
See docs/research/voicechannel-adapter.md. Mirrors v1 VoiceChannel pattern but delegates ML to subprocess.

[[2026-03-27]] Fri 02:53
## Research
Thin adapter wrapping VoiceProcessManager (.90 confidence). See docs/research/voicechannel-adapter.md.

Key findings:
- ~60 LOC adapter: constructor DI for process manager, core 3 methods (name/send/receive)
- send() creates SpeakMsg, delegates to mgr.write(); receive() filters for TranscriptMsg
- Lazy spawn on first receive(); None on EOF
- Inherits ChannelPlugin defaults for send_file/send_blocks/send_image
- No brainstorm/partial handling in v1 of adapter (YAGNI)
- Added depends_on: #61 (protocol models), #62 (process manager)
- AC is sound and complete, no new tasks needed

[[2026-03-29]] Sun 16:04
[[2026-03-29]] Sun 16:02
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Implements ChannelPlugin protocol (name, send, receive) | Vague: no method signatures, no return types | Rewritten with exact signatures |
| send() writes speak message to voice process stdin | Vague: missing SpeakMsg construction, interrupt field | Refined with exact SpeakMsg fields |
| receive() reads next transcript message | Vague: missing filtering logic, EOF behavior, prompt handling | Refined with filter/EOF/prompt semantics |
| Lazy process spawn on first receive() call | Correct concept, missing mechanism | Refined: _started flag, manager.__aenter__() |
| Delegates lifecycle to VoiceProcessManager | Vague: no cleanup path | Added async context manager with __aexit__ shutdown |
| Unit tests with mocked process manager | TDD violation: belongs in separate test task | Removed, created #142 |

### Architecture Notes
- Single domain: scope:voice. Thin adapter (~60 LOC) at packages/orchestrator/src/owlbear/voice/channel.py
- No v2 ChannelPlugin Protocol class exists yet. VoiceChannel implements the interface pattern structurally (same method signatures as v1 ChannelPlugin). Formal Protocol extraction deferred until a second channel type appears (YAGNI)
- Constructor DI for VoiceProcessManager matches v1 pattern (v1/src/owlbear/voice/channel.py)
- receive() filters for TranscriptMsg with final=True only. Non-final transcripts, partials, status, and error messages are skipped. VoiceProcessError caught and returned as None (ChannelPlugin EOF contract)
- Rich methods (send_file, send_blocks, send_image) replicate v1 ChannelPlugin defaults: delegate to send() with text representation. No formal Protocol inheritance needed
- Lazy spawn pattern: manager context entered on first receive(), not on construction. Matches v1 lazy model loading pattern
- No security surface: VoiceChannel does not accept user input directly, only wraps typed messages from an owned subprocess
- No brainstorm/partial handling per YAGNI (research recommendation .90 confidence)

### Changes Made
- Rewrote AC body with 17 verifiable lines across 6 sections
- Added public API contract (class, constructor, method signatures)
- Added receive() filtering and error handling semantics
- Added async context manager lifecycle (lazy start, cleanup)
- Added rich method defaults (send_file, send_blocks, send_image)
- Added module location
- Removed test AC line, created #142 (Test: VoiceChannel adapter) at todo
- Added depends_on: #142 (TDD ordering) alongside existing #61, #62

### Dependencies
- Verified: #61 (voice protocol models) in-progress, provides SpeakMsg/TranscriptMsg types
- Verified: #62 (voice process manager) todo, provides VoiceProcessManager/VoiceProcessError
- Created: #142 (test task) at todo, added as dependency (TDD ordering)

[[2026-04-05]] Sun 19:35
## Test-Writer Notes
- RED phase already completed via companion task #142 (archived): tests/test_voice_channel.py, 22 tests
- Current state: all 22 tests PASS (implementation live at serve/orchestrator/src/owlbear/voice/channel.py)
- AC module location specifies packages/orchestrator/src/owlbear/voice/channel.py — actual location is serve/orchestrator; builder to reconcile
- No new failing tests written: contract fully covered by #142; writing duplicates would not add value
- Passing through to builder pre-existing-impl pattern

[[2026-04-06]] Mon 01:16
## Builder Notes

### Files changed
- `serve/orchestrator/src/owlbear/voice/channel.py` — implementation was already live (pre-existing-impl pattern confirmed by test-writer notes)

### Module location reconciliation
- AC specified `packages/orchestrator/src/owlbear/voice/channel.py`
- Actual location: `serve/orchestrator/src/owlbear/voice/channel.py`
- Tests import `from owlbear.voice.channel` — resolved correctly via serve/orchestrator package; no code change needed

### Test results
- 22 passed, 0 failed
- `serve/orchestrator/src/owlbear/voice/channel.py`: **100% coverage**
- No builder-discovered tests needed — TestFromAC_* classes cover all branches

### Lint
- `ruff check`: **clean**

### Evidence
- `uv run pytest tests/test_voice_channel.py -q --tb=short` → 22 passed
- `uv run ruff check serve/orchestrator/src/owlbear/voice/channel.py tests/test_voice_channel.py` → All checks passed

[[2026-04-06]] Mon 02:40
## Review Evidence

### Tests
`uv run pytest tests/test_voice_channel.py -q --tb=short` → **22 passed, 0 failed**

### Lint
`uv run ruff check serve/orchestrator/src/owlbear/voice/channel.py tests/test_voice_channel.py` → **All checks passed**

### Coverage
`serve/orchestrator/src/owlbear/voice/channel.py`: **100%** (40/40 stmts)

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `VoiceChannel` class with `__aenter__`/`__aexit__` | channel.py:13, 80–84 | TestFromAC_Lifecycle | PASS |
| `__init__(manager: VoiceProcessManager)` no default | channel.py:22 (`*` keyword-only, no default) | all VoiceChannel(manager=mgr) calls | PASS |
| `name` returns `"voice"` | channel.py:28 | test_name_property_returns_voice | PASS |
| `async send(message: str) -> None` | channel.py:35 | test_send_is_async_method | PASS |
| `async receive(*, prompt=None) -> str \| None` | channel.py:40 | test_receive_is_async_method | PASS |
| `SpeakMsg(type="speak", text=..., interrupt=False)` → `manager.send()` | channel.py:37 (type defaults via Literal) | test_send_sets_exact_speak_msg_fields | PASS |
| prompt → `send(prompt)` before listening | channel.py:48–49 | test_prompt_sent_before_listening | PASS |
| Lazy `manager.__aenter__()` on first receive | channel.py:92–95 | test_first_receive_enters_manager | PASS |
| `_started: bool` flag | channel.py:25 | test_second_receive_does_not_re_enter_manager (call_count==1) | PASS |
| Loop, skip non-`TranscriptMsg(final=True)` | channel.py:50–55 | test_skips_status_msg_..., test_skips_partial_and_error_msgs, test_skips_non_final | PASS |
| Returns `TranscriptMsg.text` | channel.py:55 | test_returns_text_for_final_transcript | PASS |
| Returns `None` on `VoiceProcessError` | channel.py:52–53 | test_returns_none_on_voice_process_error | PASS |
| `__aenter__` returns `self` | channel.py:81 | test_aenter_returns_self | PASS |
| `__aexit__` → `shutdown()` if `_started` | channel.py:83–84 | test_aexit_calls_shutdown_if_started | PASS |
| `__aexit__` no-op if never started | channel.py:83–84 | test_aexit_noop_if_never_started | PASS |
| `send_file` → `f"[{caption}] {path}"` or `str(path)` | channel.py:62–63 | test_send_file_delegates_to_send_with_path_text | **LAX** |
| `send_blocks` → `text_fallback` via `send()` | channel.py:65–67 | test_send_blocks_delegates_to_send_with_fallback | PASS |
| `send_image(caption)` → `caption` via `send()` | channel.py:69–71 | test_send_image_with_caption_sends_caption | PASS |
| `send_image(no caption)` → `"[image]"` via `send()` | channel.py:69–71 | test_send_image_without_caption_sends_image_placeholder | PASS |

---

### Critical Finding — 5.0 LAX Assertion

**`test_send_file_delegates_to_send_with_path_text`** uses an `or` assertion:
```python
assert "audio.mp3" in sent_msg.text or "My file" in sent_msg.text
```
**Mutation test failure:** If the implementation returned only `str(path)` (i.e., `"audio.mp3"` without the caption bracket), the assert would still pass via the first clause. The AC specifies `f"[{caption}] {path}"` when caption is present — both bracketed caption AND path must appear together. The `or` allows either alone to satisfy the test.

**No compensating `TestBuilderDiscovered_*` test exists.** Builder notes explicitly state "TestFromAC_* classes cover all branches."

Per rule 5.0: LAX assertion with no compensating test = FAIL.

**Fix required (test-writer):** Tighten to:
```python
assert sent_msg.text == "[My file] audio.mp3"
```

---

### Informational (non-blocking)
- **6.1 Constructor signature:** AC specifies `__init__(manager: VoiceProcessManager)` (positional allowed); implementation uses `def __init__(self, *, manager: VoiceProcessManager)` (keyword-only). More restrictive than spec — consistent with project DI style, tests pass.
- **6.1 Module location:** AC says `packages/orchestrator/...`; actual is `serve/orchestrator/...`. Builder documented reconciliation; import resolves correctly. Consider updating AC for future reference.
- **5.7 Builder process:** CLEAN — 1 build cycle, no retries.

---

### Deductions
- −0.12: LAX assertion on `send_file` with caption; mutation not caught; no compensating test

**Confidence: 0.88 → FAIL**

**Target: todo** — implementation is correct; test-writer tightens `test_send_file_delegates_to_send_with_path_text` assertion.

[[2026-04-06]] Mon 03:04
Retry cycle — reviewer cited LAX assertion in test_send_file_delegates_to_send_with_path_text (rule 5.0: `or` allows either clause alone).

w-tdd-red Step 1b classification: weak test / code quality finding (NOT missing AC coverage) → pass-through applies.

Implementation is already correct and 22 tests pass. Cannot add new tests that satisfy RED requirement (they'd PASS immediately). Cannot modify existing passing tests (w-tdd-red rule).

Passing to builder to tighten assertion:
  assert sent_msg.text == "[My file] audio.mp3"
and add without-caption variant:
  assert sent_msg.text == "audio.mp3"

[[2026-04-06]] Mon 03:53
## Builder Notes (retry cycle)

### Files changed
- `tests/test_voice_channel.py` — tightened LAX assertion; added `TestBuilderDiscovered_SendFileNoCap`

### Change details
- **Tightened**: `test_send_file_delegates_to_send_with_path_text` — replaced weak `or` assertion with exact match: `assert sent_msg.text == "[My file] audio.mp3"`
- **Added**: `TestBuilderDiscovered_SendFileNoCap.test_send_file_no_caption_sends_str_path` — asserts `sent_msg.text == "audio.mp3"` (no-caption path). Passes immediately (implementation already correct); no RED phase possible for a test verifying an already-correct code path.
- No implementation changes required — `channel.py` was already correct.

### Test results
- 23 passed, 0 failed (was 22; +1 builder-discovered test)
- `serve/orchestrator/src/owlbear/voice/channel.py`: **100% coverage** (40/40 stmts)

### Lint
- `ruff check`: **clean**

### Evidence
- `uv run pytest tests/test_voice_channel.py -q --tb=short` → 23 passed
- `uv run ruff check serve/orchestrator/src/owlbear/voice/channel.py tests/test_voice_channel.py` → All checks passed
- Commit: `280a316`

[[2026-04-06]] Mon 04:23
## Review Evidence (retry cycle)

### Tests
`uv run pytest tests/test_voice_channel.py -q --tb=short` → **23 passed, 0 failed** (independently verified via quality-runner)

### Lint
`ruff check serve/orchestrator/src/owlbear/voice/channel.py tests/test_voice_channel.py` → **clean**

### Coverage
`owlbear.voice.channel`: **100%** (40/40 stmts)

---

### Previous FAIL Resolution

**LAX assertion** (cycle-1 finding) in `test_send_file_delegates_to_send_with_path_text`:
- Old: `assert "audio.mp3" in sent_msg.text or "My file" in sent_msg.text` — allowed either clause alone
- New: `assert sent_msg.text == "[My file] audio.mp3"` — exact equality; mutation test passes ✓

**Added** `TestBuilderDiscovered_SendFileNoCap.test_send_file_no_caption_sends_str_path`:
- `assert sent_msg.text == "audio.mp3"` — exact, covers no-caption path ✓

Both changes are **strengthenings**, not weakenings. PRESERVED/STRENGTHENED — no WEAKENED/REMOVED violations.

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `VoiceChannel` class with `__aenter__`/`__aexit__` | channel.py:13, 80–84 | TestFromAC_Lifecycle | PASS |
| `__init__(manager: VoiceProcessManager)` no default | channel.py:22 (keyword-only `*`) | all VoiceChannel(manager=mgr) calls | PASS |
| `name` returns `"voice"` | channel.py:28 | test_name_property_returns_voice | PASS |
| `async send(message: str) -> None` | channel.py:35 | test_send_is_async_method | PASS |
| `async receive(*, prompt=None) -> str \| None` | channel.py:40 | test_receive_is_async_method | PASS |
| `SpeakMsg(type="speak", ...)` → `manager.send()` | channel.py:37 | test_send_sets_exact_speak_msg_fields | PASS |
| prompt → `send(prompt)` before listening | channel.py:48–49 | test_prompt_sent_before_listening | PASS |
| Lazy `manager.__aenter__()` on first receive | channel.py:92–95 | test_first_receive_enters_manager | PASS |
| `_started: bool` flag | channel.py:25 | test_second_receive_does_not_re_enter_manager | PASS |
| Loop, skip non-`TranscriptMsg(final=True)` | channel.py:50–55 | test_skips_status_msg, test_skips_partial_and_error_msgs, test_skips_non_final | PASS |
| Returns `TranscriptMsg.text` | channel.py:55 | test_returns_text_for_final_transcript | PASS |
| Returns `None` on `VoiceProcessError` | channel.py:52–53 | test_returns_none_on_voice_process_error | PASS |
| `__aenter__` returns `self` | channel.py:81 | test_aenter_returns_self | PASS |
| `__aexit__` → `shutdown()` if `_started` | channel.py:83–84 | test_aexit_calls_shutdown_if_started | PASS |
| `__aexit__` no-op if not started | channel.py:83–84 | test_aexit_noop_if_never_started | PASS |
| `send_file` caption → `f"[{caption}] {path}"` | channel.py:62–63 | test_send_file_delegates_to_send_with_path_text | PASS (tightened) |
| `send_file` no-caption → `str(path)` | channel.py:62–63 | test_send_file_no_caption_sends_str_path | PASS |
| `send_blocks` → `text_fallback` | channel.py:65–67 | test_send_blocks_delegates_to_send_with_fallback | PASS |
| `send_image` with caption → caption | channel.py:69–71 | test_send_image_with_caption_sends_caption | PASS |
| `send_image` no caption → `"[image]"` | channel.py:69–71 | test_send_image_without_caption_sends_image_placeholder | PASS |

---

### Deductions
None — prior −0.12 deduction fully resolved; no new issues found.

**Confidence: 0.95 → PASS**

[[2026-04-06]] Mon 05:31
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is 5-line identity stub — no module registry or channel table. No update surface exists. |
| 2 | Module docstrings | Yes | Verified | `serve/orchestrator/src/owlbear/voice/channel.py`: module docstring, class docstring, all public methods (`name`, `send`, `receive`, `send_file`, `send_blocks`, `send_image`, `_ensure_started`) have accurate docstrings. No edits needed. |
| 3 | External attribution | No | N/A | Design patterns sourced from v1 internal (`v1/src/owlbear/voice/channel.py`); MCP SDK studied but not used in design decisions (all attribution rows in research → v1 internal). No new row needed in `sources/overview.md`. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/voicechannel-adapter.md` exists and is complete. Task body references stale path `docs/research/voicechannel-adapter.md` — informational gap only, not blocking. Follow-up tasks checked; research notes "no new tasks needed." |

### Files Updated
None — all checks passed without requiring edits.

### Scratch Files
None found matching `.owlbear/scratch/63-*`.

[[2026-04-06]] Mon 06:23
## Audit\n### AC Verification\n21 AC lines verified — all PASS. Key spot-checks: VoiceChannel class (channel.py:14), async context manager (80-84), lazy start (91-95), SpeakMsg construction (38), VoiceProcessError handling (52-53), send_file with tightened assertion, all rich methods.\n\n### Test Results\n- pytest (task-scoped): 23 passed, 0 failed\n- pytest (full suite): 2945 passed, 581 failed (all outside task scope), 18 skipped\n- ruff: All checks passed\n\n### Architect Quality: 4/5\nAC rewritten with 17 verifiable lines across 6 sections. Minor gap: stale packages/ path reconciled by builder.\n\n### Deduction Breakdown\n- Module path AC imprecision: -0.02\n\n### Confidence: 0.98\n### Action: archive
