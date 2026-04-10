---
id: 747
title: 'P1-02: Delete all voice I/O code and test files'
status: in-progress
priority: critical
created: '2026-04-10T10:36:20.186913+00:00'
updated: '2026-04-10T11:57:00.792014+00:00'
tags:
- phase-1
- type:cleanup
- cleanup
- scope-reduction
parent: 745
depends_on: []
blocked: false
block_reason: null
claimed_by: full-jay
claimed_at: '2026-04-10T11:57:00.792014+00:00'
---
## Context
Brief: see parent #745. Scratch tier — directory and file deletion.

No non-voice modules import from `owlbear.voice` or `owlbear_voice` — verified by codebase grep. Clean cut.

## Acceptance Criteria
1. `serve/voice/` directory deleted entirely (pyproject.toml, src/owlbear_voice/, tests/)
2. `serve/orchestrator/src/owlbear/voice/` directory deleted entirely (4 files: __init__.py, channel.py, process.py, protocol.py)
3. All 6 voice I/O test files deleted:
   - `tests/test_voice_channel.py`
   - `tests/test_voice_process_manager.py`
   - `tests/test_voice_process_manager_kill_62.py`
   - `tests/test_voice_protocol.py`
   - `tests/test_voice_stt.py`
   - `tests/test_voice_tts.py`
4. `grep -r "from owlbear.voice\|from owlbear_voice\|import owlbear.voice\|import owlbear_voice" serve/ tests/` returns zero matches

## CRITICAL
- Do NOT delete anything under `share/agents/`, `share/skills/`, or `share/instructions/`
- Do NOT touch ideation domain voices (architect-voice, critic-voice, etc.)
- Verify no non-voice module imports voice packages before deleting

## Files
- Delete: `serve/voice/` (entire directory)
- Delete: `serve/orchestrator/src/owlbear/voice/` (entire directory)
- Delete: `tests/test_voice_channel.py`, `tests/test_voice_process_manager.py`, `tests/test_voice_process_manager_kill_62.py`, `tests/test_voice_protocol.py`, `tests/test_voice_stt.py`, `tests/test_voice_tts.py`

[[2026-04-10]]
## Test-Writer Notes
- Test file: tests/test_delete_voice_io_747.py
- Classes: TestFromAC_VoicePackageRemoval, TestFromAC_OrchestratorVoiceRemoval, TestFromAC_VoiceTestFileRemoval, TestFromAC_NoVoiceImportsRemaining
- Tests per category: happy 0, edge 0, error 0, boundary 0 (deletion-verification: 18)
- Total: 18 tests, all FAIL (AssertionError — targeted files/dirs still exist)
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1: serve/voice/ deleted | test_serve_voice_dir_does_not_exist, test_serve_voice_pyproject_does_not_exist, test_serve_voice_src_does_not_exist, test_owlbear_voice_package_does_not_exist, test_serve_voice_tests_dir_does_not_exist |
| AC2: serve/orchestrator/src/owlbear/voice/ deleted | test_orchestrator_voice_dir_does_not_exist, test_orchestrator_voice_init_does_not_exist, test_orchestrator_voice_channel_does_not_exist, test_orchestrator_voice_process_does_not_exist, test_orchestrator_voice_protocol_does_not_exist |
| AC3: 6 test files deleted | test_test_voice_channel_does_not_exist, test_test_voice_process_manager_does_not_exist, test_test_voice_process_manager_kill_62_does_not_exist, test_test_voice_protocol_does_not_exist, test_test_voice_stt_does_not_exist, test_test_voice_tts_does_not_exist |
| AC4: zero voice imports in serve/ and tests/ | test_no_voice_imports_in_serve_or_tests, test_no_owlbear_voice_subpackage_imports_in_serve |

Commit: 40ce71f9 — test: add failing tests for voice I/O deletion (#747, test-writer)