---
id: 821
title: Tests — Compat alias removal + import migration
status: archived
priority: medium
created: '2026-04-10T21:22:46.872069+00:00'
updated: '2026-04-15T12:49:15.109707+00:00'
tags:
- phase-2
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 820
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify no `TaskRecord` references remain in workspace (grep verification)
- Tests verify all engine imports use `owlbear_kanban` namespace
- Tests verify existing test files import from correct package
- Tests fail RED before migration

## Context

Phase 2, step 5. Depends on #820 (adapter slimmed).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/821-compat-alias-removal-tests.md
- Sources: 7 studied, 7 high-relevance (all codebase/design doc)
- Recommendation: Hybrid AST + string-grep test file, 3 classes / 7 tests (confidence: .92)
  - AC1: 3 tests grep serve/ and tests/ for TaskRecord (~127 refs currently, all RED)
  - AC2: 2 tests verify server.py TYPE_CHECKING import and stale owlbear_mcp_kanban namespace imports in 4 test files
  - AC3: 2 tests verify 7 test files importing TaskRecord from owlbear_kanban.models
  - AC4: meta-criterion satisfied by all 7 tests failing RED
- Tier: T1 (autonomous, TDD RED)
- Follow-up tasks created: none (GREEN phase #822 already exists at backlog)
- Decision requests: none
[[2026-04-12]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: write RED tests for compat alias removal verification |
| Interface clarity | PASS | AC slightly vague ("workspace", "engine imports") but research doc + inline summary provide precise mappings (3 classes, 7 tests, specific files/counts) |
| Dependency correctness | PASS | #820 (adapter slimming) is correct prerequisite. #820 currently in research — orchestrator handles dispatch ordering |
| Module layering | N/A | Test code only |
| TDD compliance | PASS | This IS the TDD RED phase. #822 is corresponding GREEN |
| KISS/YAGNI | PASS | 3 classes, 7 tests — minimal. Hybrid AST+grep matches established patterns |
| Premise challenge | PASS | Valid step in kanban extraction sequence (phase 2, step 5) |
| Pattern consistency | PASS | Follows #800 (AST+string grep) and #817 (rglob+AST) precedents |
| Security surface | N/A | Test code, no new system boundaries |
| Single domain | PASS | mcp-kanban test domain only |

### Builder Guidance (AC Precision)
- AC1 scope: `serve/kanban/src/**/*.py`, `serve/mcp-kanban/src/**/*.py`, `tests/**/*.py` — exclude self (`test_compat_alias_removal_821.py`), `.owlbear/`, `.md` files
- AC2 targets: (a) server.py TYPE_CHECKING import should not reference TaskRecord, (b) 4 test files should not import from stale `owlbear_mcp_kanban.{engine,task_io,config_loader}` namespaces
- AC3 specifics: 7 test files that import TaskRecord from owlbear_kanban.models should import Task instead
- Self-exclusion required: test file references TaskRecord in docstrings/assertions

### Challenge Results
- Challenger: FALLBACK — agent unavailable
- Architect response: proceeded — T1 test task with established patterns, .92 research confidence

### Verdict: APPROVE
### Action Taken: Advanced #821 backlog → todo. Research doc comprehensive, patterns established, AC precision documented in builder guidance above.
[[2026-04-12]]
## Test-Writer Notes

**Test file:** `tests/test_compat_alias_removal_821.py` (pre-existing file, ruff fixes applied)

| Class | AC | Tests | Category |
|-------|----|-------|----------|
| `TestFromAC_NoTaskRecordReferences` | AC1 | 3 | boundary/grep |
| `TestFromAC_EngineImportsOwlbearKanban` | AC2 | 2 | boundary/AST |
| `TestFromAC_TestFileImports` | AC3 | 2 | boundary/AST |

**Total: 7 tests — all FAIL (0 passed, 7 failed). Ruff: clean.**

**AC coverage:**
| AC | Tests | RED reason |
|----|-------|------------|
| AC1 — zero TaskRecord refs in engine src | test_no_taskrecord_in_engine_source | 18 refs in models.py/__init__.py/engine.py/task_io.py |
| AC1 — zero TaskRecord refs in MCP src | test_no_taskrecord_in_mcp_adapter_source | 3 refs in server.py |
| AC1 — zero TaskRecord refs in tests | test_no_taskrecord_in_tests | 141 refs across test files |
| AC2 — server.py no TaskRecord TYPE_CHECKING | test_server_no_taskrecord_import | server.py line 24 still imports TaskRecord |
| AC2 — no stale owlbear_mcp_kanban.* imports | test_no_stale_mcp_namespace_imports_in_tests | 4 test files use stale namespaces |
| AC3 — targeted test files don't import TaskRecord | test_target_files_do_not_import_taskrecord | 6 target files still import TaskRecord |
| AC3 — targeted files import Task | test_target_files_import_task | 4 files missing Task import |
| AC4 | — | meta-criterion: all 7 fail RED ✓ |

**Self-exclusion:** `_SELF = Path(__file__)` prevents false positives from TaskRecord string literals in this test file's own source.

**Hybrid approach:** string grep (AC1) + AST import inspection (AC2, AC3) — matches #800/#817 precedents.
[[2026-04-12]]
## Test-Writer Notes

**Test file:** `tests/test_compat_alias_removal_821.py`

### Classes and test count

| Class | AC | Tests |
|-------|----|-------|
| `TestFromAC_NoTaskRecordReferences` | AC1 | 3 |
| `TestFromAC_EngineImportsOwlbearKanban` | AC2 | 2 |
| `TestFromAC_TestFileImports` | AC3 | 2 |
| **Total** | AC1–AC4 | **7** |

### Categories

| Category | Count | Notes |
|----------|-------|-------|
| Grep / string scan | 3 | Rglob over src dirs + tests dir with self-exclusion |
| AST import inspection | 4 | `_imports_from`, `_stale_module_imports` helpers; walks full AST including TYPE_CHECKING blocks |

### AC coverage table

| AC | Test(s) | RED reason |
|----|---------|------------|
| AC1 — no TaskRecord refs in engine src | `test_no_taskrecord_in_engine_source` | 18 refs found |
| AC1 — no TaskRecord refs in MCP adapter src | `test_no_taskrecord_in_mcp_adapter_source` | 3 refs found |
| AC1 — no TaskRecord refs in tests | `test_no_taskrecord_in_tests` | 141 refs found |
| AC2 — server.py TYPE_CHECKING import gone | `test_server_no_taskrecord_import` | `from owlbear_kanban.models import TaskRecord` present |
| AC2 — stale mcp namespace tests gone | `test_no_stale_mcp_namespace_imports_in_tests` | 4 test files use `owlbear_mcp_kanban.{engine,task_io,config_loader}` |
| AC3 — target files don't import TaskRecord | `test_target_files_do_not_import_taskrecord` | 5 of 6 targets still import TaskRecord |
| AC3 — target files import Task | `test_target_files_import_task` | 4 checked files don't import Task |
| AC4 — all fail RED | _meta_ | Satisfied: 7 failed, 0 passed |

### Fail verification

`pytest tests/test_compat_alias_removal_821.py -v` → **7 failed, 0 passed** ✓  
Ruff: **All checks passed** ✓

### Self-exclusion

`test_compat_alias_removal_821.py` excluded from AC1 grep scan via `Path(__file__)` comparison — file contains "TaskRecord" in docstrings and assertion messages.

### Note

Research doc predicted 7 target test files for AC3; grep found 6 active files importing TaskRecord from `owlbear_kanban.models`. The 7th (`test_rename_taskrecord_to_task_800.py`) uses TaskRecord only in string-literal assertions — no model import — consistent with §3a classification as AC1-only. AC3 test covers the verified 6 files.
[[2026-04-12]]
## Review Evidence

### Tests
- **pytest** `tests/test_compat_alias_removal_821.py`: **0 passed, 7 failed** — all RED as required for TDD RED phase ✓
- **ruff**: clean, 0 violations ✓

### Test Failure Verification (independent run via quality-runner)
| Test | Failure Evidence |
|------|-----------------|
| `test_no_taskrecord_in_engine_source` | 5 refs in engine src (models.py, __init__.py) |
| `test_no_taskrecord_in_mcp_adapter_source` | 3 refs in server.py (line 24 TYPE_CHECKING import, line 154 annotation, line 155 docstring) |
| `test_no_taskrecord_in_tests` | 144 refs across test files |
| `test_server_no_taskrecord_import` | `from owlbear_kanban.models import TaskRecord` present at line 24 (TYPE_CHECKING block) |
| `test_no_stale_mcp_namespace_imports_in_tests` | 6 test files use stale `owlbear_mcp_kanban.*` namespaces |
| `test_target_files_do_not_import_taskrecord` | 6 target files still import TaskRecord |
| `test_target_files_import_task` | 4 files missing Task import |

### AC Compliance
| AC | Test(s) | Evidence | Status |
|----|---------|----------|--------|
| AC1 — no TaskRecord refs in workspace (engine src, MCP src, tests) | 3 tests — grep scan with self-exclusion | Correctly detects refs across all 3 scopes; strong assertion (`assert not hits`) | PASS |
| AC2 — engine imports use owlbear_kanban namespace; server.py no TaskRecord TYPE_CHECKING | 2 tests — AST import inspection | `_imports_from` uses `ast.walk()`, traverses into TYPE_CHECKING blocks correctly; server.py line 24 detected | PASS |
| AC3 — target test files replace TaskRecord with Task | 2 tests — AST import inspection on 6 target files | `_TARGET_TEST_FILES` covers 6 files; 4-file subset for positive Task-import assertion documented with reason | PASS |
| AC4 — all tests fail RED | meta-criterion | 7/7 fail, 0 pass | PASS |

### Assertion Strength Assessment
- **AC1 grep assertions**: `assert not hits` is strong — any single remaining reference would fail. Text grep intentionally strict (all references including docstrings), consistent with "no `TaskRecord` references remain" in AC wording.
- **AC2 AST inspection**: `_imports_from` uses `ast.walk()` which traverses `if TYPE_CHECKING:` blocks as ordinary `If` nodes — TYPE_CHECKING import at server.py:24 correctly detected. Not a lazy assertion.
- **AC3 import assertions**: both negative (no TaskRecord) and positive (Task present) assertions — paired coverage prevents vacuous GREEN from deletion-only.

### Self-Exclusion Verification
`_SELF = Path(__file__)` correctly excludes the test file from AC1 grep. File contains "TaskRecord" in docstrings and assertion messages — exclusion is required and implemented correctly.

### TestFromAC_* Modifications
None detected. Classes `TestFromAC_NoTaskRecordReferences`, `TestFromAC_EngineImportsOwlbearKanban`, `TestFromAC_TestFileImports` are intact and match test-writer notes.

### Minor Count Discrepancies (notes, not defects)
- Test-writer reported 18 engine refs / 4 stale namespace files; quality-runner observed 5 engine refs / 6 stale files — counts reflect incremental changes between runs. Tests detect violations correctly regardless of exact count.

### Deductions
None.

### Verdict
PASS #821 → docs | confidence .96
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task; no new public API, no behavior change, no copilot-instructions.md update needed |
| 2 | Module docstrings | Yes | Verified | Module docstring accurate; all 3 TestFromAC_* classes have class docstrings; all 7 test methods have docstrings; all 3 helpers (_taskrecord_refs, _imports_from, _stale_module_imports) have docstrings. No updates needed. |
| 3 | External attribution | No | N/A | Hybrid AST+grep approach references internal precedents (#800, #817) only — no external repos or articles. sources/overview.md not applicable. |
| 4 | CLI changes | No | N/A | No CLI changes. README.md not applicable. |
| 5 | Research doc | Yes | Verified | .owlbear/research/821-compat-alias-removal-tests.md exists on disk and is linked from task body under ## Research. |

### Files Updated
- None

### Scratch Files Cleaned
- None found (.owlbear/scratch/821-* — no matches)
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — no TaskRecord refs in workspace | 3 tests in `TestFromAC_NoTaskRecordReferences`: grep with self-exclusion across engine src, MCP src, tests/ | PASS |
| AC2 — engine imports use owlbear_kanban namespace | 2 tests in `TestFromAC_EngineImportsOwlbearKanban`: AST inspection of server.py + stale namespace detection | PASS |
| AC3 — test files import from correct package | 2 tests in `TestFromAC_TestFileImports`: AST import check on 6 target files (negative + positive assertions) | PASS |
| AC4 — tests fail RED before migration | Reviewer verified 7 failed / 0 passed at commit time; now 7 pass (GREEN completed downstream) | PASS |

### Test Results
- pytest (task-scoped): 7 passed, 0 failed (tests now GREEN — downstream migration completed)
- pytest (full suite): 192 failed, 4386 passed, 8 skipped — 0 failures in #821 scope (192 are pre-existing)
- ruff: 3 violations, none in #821 scope

### Architect Quality: 4/5
AC1-3 specific enough for verification. Minor scope clarification ("workspace" → specific dirs) provided by architect builder guidance. AC4 meta-criterion clear.

### Deduction Breakdown
- No AC lines without evidence: 0
- Lint violations in scope: 0
- AC quality > 3: no deduction
- Reviewer evidence present and detailed: no deduction
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 218dd103 | test | tests/test_compat_alias_removal_821.py | #821 |
| c70caaef | chore | kanban task file | #821 |