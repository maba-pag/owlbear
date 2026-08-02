---
id: 747
title: 'P1-02: Delete all voice I/O code and test files'
status: archived
priority: medium
created: '2026-04-10T10:36:20.186913+00:00'
updated: '2026-04-10T13:43:34.212440+00:00'
tags:
- phase-1
- type:cleanup
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
[[2026-04-10]]

## Builder Notes

### Files Changed

- Deleted: `serve/voice/` (entire directory — pyproject.toml, src/owlbear_voice/, tests/)
- Deleted: `serve/orchestrator/src/owlbear/voice/` (4 files: __init__.py, channel.py, process.py, protocol.py)
- Deleted: `tests/test_voice_channel.py`, `tests/test_voice_process_manager.py`, `tests/test_voice_process_manager_kill_62.py`, `tests/test_voice_protocol.py`, `tests/test_voice_stt.py`, `tests/test_voice_tts.py`

### Test Results

- RED verified: 18/18 FAILED before deletions
- GREEN: 18/18 PASSED after deletions
- Full suite canary (112 tests): all passed — no regressions

### Lint

- ruff: clean (0 issues on test file)

### Coverage

- No source code added — deletion task only; coverage N/A

### Commit

- `26fa00a1` — feat: delete voice I/O package, orchestrator voice module, and test files (#747, builder)
[[2026-04-10]]

## Review Evidence

### Tests

pytest: __18 passed, 0 failed__ (tests/test_delete_voice_io_747.py)
Full suite canary not re-run independently — builder reports 112 passed, no regressions.

### Lint

ruff: __clean__ — 0 violations on test file.

### Coverage

N/A — deletion task, no source code added.

### Filesystem Verification (independent)

- `serve/voice/**` → file_search: __no files found__ ✓
- `serve/orchestrator/src/owlbear/voice/**` → file_search: __no files found__ ✓
- `tests/test_voice_*.py` → file_search: only `test_voice_removal_clean_build_750.py` (unrelated) — all 6 target files __absent__ ✓
- grep for voice imports in `serve/` → __0 matches__ ✓

### AC Compliance

| AC | Mapped Tests | Would Fail If AC Violated? | Verdict |
|----|-------------|---------------------------|---------|
| AC1: serve/voice/ deleted | test_serve_voice_dir_does_not_exist + 4 subdirs/files | Yes — `assert not path.exists()` fails if any remain | COVERED |
| AC2: orchestrator voice/ deleted | test_orchestrator_voice_dir_does_not_exist + 4 files | Yes — same pattern | COVERED |
| AC3: 6 test files deleted | one test per file (6 total) | Yes — same pattern | COVERED |
| AC4: zero voice imports | test_no_voice_imports_in_serve_or_tests, test_no_owlbear_voice_subpackage_imports_in_serve | Yes — regex scan fails on any match | COVERED |

### TestFromAC Integrity

No TestFromAC_* classes were modified. Builder committed only deletions (`26fa00a1`); test file is unchanged from test-writer commit `40ce71f9`.

### Test Quality

- Assertion specificity: STRONG — `assert not path.exists()` and regex-scan assertions; no lazy truthy checks.
- Coverage of AC: all 4 AC lines have 1+ tests that fail specifically on violation.
- Independence: all tests read filesystem state only; no shared mutable state.
- Names: all descriptive (e.g. `test_orchestrator_voice_channel_does_not_exist`).
- Rating: __STRONG__

### Security

No new code introduced. Test file uses `re.compile()` with a fixed pattern and `Path.rglob()` scoped to known directories — no user input, no injection surface. No concerns.

### Deductions

None.

### Verdict

Confidence: __.97__ → __PASS__
[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | Voice I/O packages removed entirely — checked copilot-instructions.md (no voice I/O mentions) and README.md (no voice I/O mentions). No documentation updates required. |
| 2 | Module docstrings | No | N/A | Deletion-only task; no Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used; pure filesystem deletion. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced for this task. |

### Files Updated

None — no docs impact.

### Scratch Files

No `.owlbear/scratch/747-*` files found.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: serve/voice/ deleted | file_search("serve/voice/**") → no files found | PASS |
| AC2: orchestrator voice/ deleted | file_search("serve/orchestrator/src/owlbear/voice/**") → no files found | PASS |
| AC3: 6 test files deleted | file_search for each of 6 files → no files found | PASS |
| AC4: zero voice imports | grep for voice imports in serve/ and tests/ → 0 matches | PASS |

### Test Results

- pytest (task-scoped): 18 passed, 0 failed
- pytest (full suite): 3081 passed, 441 failed — no failures in task scope; all pre-existing
- ruff: 0 violations

### Architect Quality: 5/5

Precise paths, exact file lists, grep verification command, explicit CRITICAL boundary guards. No builder improvisation needed.

### Deduction Breakdown

None — all AC lines evidenced, lint clean, reviewer section detailed with PASS, no task-scope failures.

### Confidence: 1.00

### Action: archive

### Commits (upstream)

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 40ce71f9 | test | tests/test_delete_voice_io_747.py | #747 |
| 26fa00a1 | feat | serve/voice/ (del), serve/orchestrator/src/owlbear/voice/ (del), 6 test files (del) | #747 |
