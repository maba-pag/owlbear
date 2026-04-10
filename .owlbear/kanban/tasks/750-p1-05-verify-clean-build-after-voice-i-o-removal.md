---
id: 750
title: 'P1-05: Verify clean build after voice I/O removal'
status: in-progress
priority: critical
created: '2026-04-10T10:36:47.180806+00:00'
updated: '2026-04-10T11:47:29.482076+00:00'
tags:
- phase-1
- type:verification
- cleanup
- scope-reduction
parent: 745
depends_on:
- 748
- 749
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Exit gate verification for the entire voice removal operation.

This task verifies the codebase is clean after all voice I/O deletions and config updates.

## Acceptance Criteria
1. `pytest` full suite passes with 0 failures (excluding e2e/api-marked tests)
2. `ruff check` passes with 0 errors across the workspace
3. `grep -r "owlbear.voice\|owlbear_voice" serve/ tests/` returns zero matches (no orphan imports)
4. `serve/voice/` does not exist
5. `serve/orchestrator/src/owlbear/voice/` does not exist
6. No `test_voice_*.py` files exist in `tests/`
7. `pyproject.toml` contains no `voice` references in ruff sources or coverage source_pkgs
8. `README.md` contains no `serve/voice/` reference

## CRITICAL
Ideation domain voices (architect-voice, critic-voice, etc.) in `share/` MUST still exist and be untouched. Verify they are NOT deleted.

## Files
- Verify absent: `serve/voice/`, `serve/orchestrator/src/owlbear/voice/`, `tests/test_voice_*.py`
- Verify clean: `pyproject.toml`, `README.md`, `uv.lock`
- Verify untouched: `share/agents/`, `share/skills/`, `share/instructions/`

[[2026-04-10]]
## Test-Writer Notes
- Test file: tests/test_voice_removal_clean_build_750.py
- Classes: TestFromAC_VoiceDirectoryRemoval, TestFromAC_VoiceTestFilesRemoval, TestFromAC_OrphanImportCleanup, TestFromAC_PyprojectTomlCleanup, TestFromAC_ReadmeCleanup
- Tests per category: happy 0, edge 0, error 0, boundary 0 — all tests are filesystem/contract assertions for cleanup verification
- Total: 9 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| AC3 (no orphan imports in serve/ + tests/) | test_no_voice_imports_in_serve, test_no_voice_imports_in_tests, test_no_voice_references_in_serve_toml_files |
| AC4 (serve/voice/ absent) | test_serve_voice_dir_does_not_exist |
| AC5 (orchestrator voice subdir absent) | test_orchestrator_voice_subdir_does_not_exist |
| AC6 (no test_voice_*.py) | test_no_test_voice_files_in_tests_dir |
| AC7 (pyproject.toml clean) | test_ruff_src_no_voice_entry, test_coverage_source_pkgs_no_owlbear_voice |
| AC8 (README.md clean) | test_readme_no_serve_voice_reference |
| AC1/AC2 (pytest+ruff pass) | Not testable from within pytest — verified by running quality suite |

CRITICAL note: share/ domain voice preservation tests were not included in RED phase (they would pass on current HEAD, violating the all-fail constraint). The builder must manually verify share/agents/ is untouched — this constraint is documented in the test file comments and task body.