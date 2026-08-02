---
id: 142
title: 'Test: VoiceChannel adapter'
status: archived
priority: medium
created: 2026-03-29 16:01:31.558582+02:00
updated: 2026-03-30 09:01:48.634053+02:00
started: 2026-03-29 16:01:45.807680+02:00
completed: 2026-03-30 09:01:02.526134+02:00
tags:
- phase-3
- ' scope:voice'
- ' type:test'
- ' test'
depends_on:
- 61
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests for VoiceChannel (#63) before implementation.

## Acceptance Criteria

### Test file
- [ ] tests/test_voice_channel.py

### Test categories (all tests must FAIL on current HEAD)

**Protocol compliance (TestFromAC_Protocol):**
- [ ] VoiceChannel has name property returning "voice"
- [ ] VoiceChannel has async send(message: str) method
- [ ] VoiceChannel has async receive(*, prompt: str | None = None) method

**send() behavior (TestFromAC_Send):**
- [ ] Creates SpeakMsg(type="speak", text=message, interrupt=False) and calls manager.send()
- [ ] Verifies exact SpeakMsg fields passed to manager

**receive() behavior (TestFromAC_Receive):**
- [ ] Returns TranscriptMsg.text when final=True TranscriptMsg received
- [ ] Skips non-TranscriptMsg messages (StatusMsg, PartialMsg, ErrorMsg)
- [ ] Skips TranscriptMsg with final=False
- [ ] Returns None when manager raises VoiceProcessError

**receive() prompt (TestFromAC_ReceivePrompt):**
- [ ] When prompt is provided, calls send(prompt) before listening

**Lazy spawn (TestFromAC_LazySpawn):**
- [ ] Manager not entered on VoiceChannel construction
- [ ] First receive() call enters manager context (calls __aenter__)
- [ ] Second receive() does not re-enter manager

**Lifecycle (TestFromAC_Lifecycle):**
- [ ] __aenter__ returns self
- [ ] __aexit__ calls manager.shutdown() if started
- [ ] __aexit__ no-op if never started

**Rich methods (TestFromAC_RichMethods):**
- [ ] send_file delegates to send() with text representation
- [ ] send_blocks delegates to send() with text_fallback
- [ ] send_image delegates to send() with caption or "[image]"

### Test approach
- All tests use AsyncMock for VoiceProcessManager (no real subprocess)
- Protocol types imported from owlbear.voice.protocol (SpeakMsg, TranscriptMsg, etc.)
- ~18 tests expected, all must fail with ImportError on current HEAD

## Context
Companion test task for #63 (VoiceChannel adapter). Tests written before implementation (TDD RED).

[[2026-03-30]] Mon 05:31
## Test-Writer Notes
- Test file: tests/test_voice_channel.py
- Classes: TestFromAC_Protocol, TestFromAC_Send, TestFromAC_Receive, TestFromAC_ReceivePrompt, TestFromAC_LazySpawn, TestFromAC_Lifecycle, TestFromAC_RichMethods
- Tests per category: happy 10, edge 3, error 2, boundary 0
- Total: 20 tests, all FAIL (ImportError: No module named 'owlbear.voice.channel') v
- ruff: clean
- AC coverage:
  | AC Line | Test(s) | Category |
  | VoiceChannel.name == 'voice' | test_name_property_returns_voice | happy |
  | send() is async | test_send_is_async_method | happy |
  | receive() is async | test_receive_is_async_method | happy |
  | Creates SpeakMsg and calls manager.send() | test_send_calls_manager_with_speak_msg | happy |
  | Exact SpeakMsg fields | test_send_sets_exact_speak_msg_fields | happy |
  | Returns TranscriptMsg.text when final=True | test_returns_text_for_final_transcript | happy |
  | Skips StatusMsg | test_skips_status_msg_and_returns_next_transcript | edge |
  | Skips PartialMsg/ErrorMsg | test_skips_partial_and_error_msgs | edge |
  | Skips non-final TranscriptMsg | test_skips_non_final_transcript | edge |
  | Returns None on VoiceProcessError | test_returns_none_on_voice_process_error | error |
  | prompt calls send before listening | test_prompt_sent_before_listening, test_prompt_send_occurs_before_manager_receive | happy |
  | Manager not entered on construction | test_manager_not_entered_on_construction | error |
  | First receive() enters manager | test_first_receive_enters_manager | happy |
  | Second receive() does not re-enter | test_second_receive_does_not_re_enter_manager | happy |
  | __aenter__ returns self | test_aenter_returns_self | happy |
  | __aexit__ calls shutdown if started | test_aexit_calls_shutdown_if_started | happy |
  | __aexit__ no-op if never started | test_aexit_noop_if_never_started | happy |
  | send_file delegates to send() | test_send_file_delegates_to_send_with_path_text | happy |
  | send_blocks delegates to send() | test_send_blocks_delegates_to_send_with_fallback | happy |
  | send_image with/without caption | test_send_image_with_caption_sends_caption, test_send_image_without_caption_sends_image_placeholder | happy |

[[2026-03-30]] Mon 07:46
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear/voice/channel.py (new), packages/orchestrator/src/owlbear/voice/process.py (new), tests/test_voice_channel.py (TestBuilderDiscovered added)
- Tests: 27 passed (22 TestFromAC + 5 TestBuilderDiscovered), coverage 100% on channel.py and process.py
- Lint: ruff clean
- Evidence: 27 passed in 0.28s, ruff all checks passed
- Fixes applied: None - clean GREEN phase

[[2026-03-30]] Mon 08:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Both packages already in directory table; no convention change |
| 2 | Docstrings | Yes | Pass | channel.py and process.py: all public classes and methods have accurate docstrings |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
None

### Scratch Files Cleaned
None

[[2026-03-30]] Mon 09:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| tests/test_voice_channel.py exists | File read, 362 lines | PASS |
| TestFromAC_Protocol class | 3 tests: name, send async, receive async | PASS |
| TestFromAC_Send class | 2 tests: SpeakMsg creation, exact fields | PASS |
| TestFromAC_Receive class | 5 tests: final transcript, skip StatusMsg, skip Partial/Error, skip non-final, VoiceProcessError | PASS |
| TestFromAC_ReceivePrompt class | 2 tests: prompt sent before listening, ordering verified via mock_calls | PASS |
| TestFromAC_LazySpawn class | 3 tests: no enter on construction, first receive enters, second no re-enter | PASS |
| TestFromAC_Lifecycle class | 3 tests: aenter returns self, aexit shutdown if started, aexit noop if not | PASS |
| TestFromAC_RichMethods class | 4 tests: send_file, send_blocks, send_image w/caption, send_image w/o caption | PASS |
| All tests use AsyncMock | Confirmed via _make_manager helper and test imports | PASS |
| ~18 tests expected | 22 TestFromAC + 5 TestBuilderDiscovered = 27 total; exceeds specification | PASS |

### Test Results
- pytest (task-scoped): 27 passed in 0.28s
- pytest (full suite): 747 passed, 172 failed (all pre-existing from other tasks), 4 errors (pre-existing)
- ruff: All checks passed

### Upstream Commits
- bdc23df test: add failing tests for VoiceChannel adapter (#142, test-writer)
- 1229d18 feat: implement VoiceChannel adapter (#142, builder)
- All deliverables clean in git status (no uncommitted changes)

### AC Quality Score: 5/5
AC was highly specific with exact method signatures, message types, and expected behaviors. All test categories mapped cleanly. Builder required no improvisation.

### Missing Reviewer Evidence
No Review Evidence section in task body. Writer (docs gate) was present. Deduction applied: -.02

### Deduction breakdown
- -.02 Missing reviewer evidence section in task body

### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 09:01
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f710b60 | chore | kanban/tasks/142-*.md | #142 |
