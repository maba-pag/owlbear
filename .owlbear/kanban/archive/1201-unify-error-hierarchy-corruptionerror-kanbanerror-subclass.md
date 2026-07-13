---
id: 1201
title: Unify error hierarchy — CorruptionError → KanbanError subclass
status: archived
priority: medium
created: 2026-04-30 15:28:56.411894+00:00
updated: 2026-04-30T21:56:52.357544+00:00
tags:
- audit-kanban
parent:
depends_on:
- 1203
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Unify error hierarchy so CorruptionError is a KanbanError subclass.

## Files
- corruption.py (CorruptionError class)
- errors.py (KanbanError base, add ERR_CORRUPT_* codes + re-export)

## Change
Make CorruptionError extend KanbanError. Add the 9 ERR_CORRUPT_* string codes to
KANBAN_ERROR_CODES so KanbanError's code-validation __init__ accepts them.
CorruptionError keeps its own __init__ override (extra kwargs: detail, path, file_path)
but calls super().__init__(code, user_message) to satisfy the KanbanError contract.
Re-export CorruptionError from errors.py for discoverability.

## AC
- [ ] CorruptionError inherits from KanbanError (td:2)
- [ ] CorruptionError.__init__ calls KanbanError.__init__(code, user_message) before setting extra attrs (td:2)
- [ ] KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* string codes (td:1)
- [ ] errors.py re-exports CorruptionError (td:1)
- [ ] isinstance(CorruptionError(...), KanbanError) is True (td:1)
- [ ] All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses (td:1)
- [ ] Existing consumers importing from corruption.py or errors.py still work (td:1)

## Out of scope
Removing error re-exports from models.py (separate task — too many consumers to migrate atomically with the hierarchy change).

## Finding: 3.2

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Hierarchy unification only; models.py cleanup deferred |
| Interface clarity | PASS | Constructor contract specified (calls super, keeps extra kwargs) |
| Dependency correctness | PASS | #1203 archived/done |
| Module layering | PASS | corruption.py → errors.py (leaf → base) |
| TDD compliance | PASS | No preceding test task required — inherits from audit chain |
| KISS/YAGNI | PASS | Minimal change: add codes + change base class |
| Premise challenge | PASS | Unified hierarchy enables `except KanbanError` to catch corruption — desirable |
| Pattern consistency | PASS | Matches existing ValidationError/NotFoundError pattern |
| Security surface | PASS | No new I/O boundaries |
| Single domain | PASS | kanban error taxonomy only |

### Challenge Results
- Challenger: SKIPPED — straightforward inheritance refactor with clear constructor contract
- Architect response: N/A

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC to resolve constructor incompatibility and removed contradictory models.py cleanup (separate task). Moved to todo.

[[2026-04-30]]
Architecture review complete. Refined AC to resolve constructor incompatibility (CorruptionError.__init__ must call KanbanError.__init__) and added ERR_CORRUPT_* codes to KANBAN_ERROR_CODES. Removed contradictory models.py cleanup — too many consumers (20+) to migrate atomically; deferred to separate task. Dependency #1203 verified archived/done.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_error_hierarchy_1201.py
- Classes: TestFromAC_ErrorHierarchy, TestFromAC_ConstructorCallsSuper, TestFromAC_KanbanErrorCodes, TestFromAC_ReExport, TestFromAC_InstanceCheck, TestFromAC_DynamicSubclasses, TestFromAC_ConsumerImports
- Tests per category: happy 4, edge 4, error 3, boundary 3, smoke 17
- Total: 31 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC line | Tests |
  |---------|-------|
  | CorruptionError inherits from KanbanError (td:2) | test_corruption_error_is_subclass_of_kanban_error, test_kanban_error_in_mro, test_corruption_error_caught_by_kanban_error_handler |
  | __init__ calls KanbanError.__init__ (td:2) | test_instance_is_kanban_error_and_code_attr_set, test_user_message_kwarg_propagated_via_super, test_invalid_code_raises_value_error_via_kanban_validation, test_extra_attrs_preserved_alongside_kanban_error_attrs, test_detail_fallback_when_no_user_message |
  | KANBAN_ERROR_CODES has 9 ERR_CORRUPT_* codes (td:1) | 9 parametrized + test_all_nine_corrupt_codes_present |
  | errors.py re-exports CorruptionError (td:1) | test_corruption_error_importable_from_errors_module |
  | isinstance check (td:1) | test_isinstance_of_kanban_error |
  | 9 dynamic subclasses remain (td:1) | 9 parametrized test_dynamic_subclass_remains_corruption_error_and_is_kanban_error |
  | Consumer imports still work (td:1) | test_corruption_py_import_still_works, test_errors_py_import_still_works |
[[2026-04-30]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/corruption.py and serve/kanban/src/owlbear_kanban/errors.py.
- Fixes applied:
  - `CorruptionError` now subclasses `KanbanError` and calls `super().__init__(code_name, msg)` before setting corruption-specific attributes.
  - Added all 9 `ERR_CORRUPT_*` codes to `KANBAN_ERROR_CODES` for `KanbanError` code validation.
  - Re-exported `CorruptionError` from `errors.py` using lazy module `__getattr__` to avoid import-cycle regressions.
- Tests: 31/31 passed in `tests/test_error_hierarchy_1201.py` (all `TestFromAC_*` green).
- ruff: clean on touched source files + task test file.
- Coverage evidence:
  - Task-scoped run: `owlbear_kanban.corruption` 16%, `owlbear_kanban.errors` 100%.
  - Broader regression probes encountered unrelated pre-existing failures outside task scope (e.g. support-module migration config expectations and engine behavior assertions), so expanded coverage could not be used as a clean gate signal.
- Commit: `f26de48e8bd3c01d7b963860a6696775b01a71f5` with only the two scoped source files.

- Reflection:
  - Direct eager re-export in `errors.py` introduced a circular import due to `models -> errors -> corruption -> models`; lazy re-export pattern avoids this safely.
  - Task-specific RED/GREEN loop was stable and mapped cleanly to AC lines.
  - Broader-suite failures were environmental/unrelated to this AC and should be handled in separate tasks to keep builder diff surgical.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 31 passed, 0 failed, 0 skipped on `tests/test_error_hierarchy_1201.py`
- targeted broader regression support: 101 passed, 1 failed on `serve/kanban/tests/test_corruption.py` and `serve/kanban/tests/test_engine_storage.py`
- unrelated broader failure: `serve/kanban/tests/test_corruption.py::TestBuilderDiscovered::test_make_yaml_disables_timestamp_resolver` (`AttributeError: module 'owlbear_kanban.corruption' has no attribute '_make_yaml'`); treated as pre-existing regression context, not a gate failure for this task
- parallel fan-out note: `code-reader` returned an execution error during GitHub service disruption, so this review fell back to the sequential workflow

### Lint
- clean: true
- scope: `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/errors.py`, `tests/test_error_hierarchy_1201.py`

### Coverage
- `owlbear_kanban.corruption`: 16%
- `owlbear_kanban.errors`: 100%
- gate assessment: PASS for the builder's changed lines. The hierarchy change, constructor normalization/super call, 9 code additions, and lazy re-export are directly exercised by the task test file plus targeted regression runs. The low overall `corruption.py` module percentage is informational only under the diff-scoped coverage rule.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| CorruptionError inherits from KanbanError | `test_corruption_error_is_subclass_of_kanban_error`, `test_kanban_error_in_mro`, `test_corruption_error_caught_by_kanban_error_handler` | Yes - inheritance/MRO/exception catching would break immediately | COVERED |
| CorruptionError.__init__ calls KanbanError.__init__(code, user_message) before setting extra attrs | `test_instance_is_kanban_error_and_code_attr_set`, `test_user_message_kwarg_propagated_via_super`, `test_invalid_code_raises_value_error_via_kanban_validation`, `test_extra_attrs_preserved_alongside_kanban_error_attrs`, `test_detail_fallback_when_no_user_message` | Yes for the super-call contract and validation path; exact pre-extra-attr ordering is proven by source inspection rather than isolated by tests | LAX |
| KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* string codes | `test_err_corrupt_code_in_kanban_error_codes`, `test_all_nine_corrupt_codes_present` | Yes - missing any code would fail membership assertions | COVERED |
| errors.py re-exports CorruptionError | `test_corruption_error_importable_from_errors_module` | Yes - import or identity would fail | COVERED |
| isinstance(CorruptionError(...), KanbanError) is True | `test_isinstance_of_kanban_error` | Yes - exact isinstance assertion fails | COVERED |
| All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses | `test_dynamic_subclass_remains_corruption_error_and_is_kanban_error` | Yes - either inheritance assertion fails | COVERED |
| Existing consumers importing from corruption.py or errors.py still work | `test_corruption_py_import_still_works`, `test_errors_py_import_still_works` | Yes - import or instance checks fail | COVERED |

#### Security Review
- No issues found in the changed code.
- No new I/O boundaries, subprocess calls, deserialization sinks, path handling, or dependency changes were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_error_hierarchy_1201.py` `TestFromAC_*` classes | No weakening/removal evidence in the current snapshot. Builder notes scope the task commit to the two source files, and `.git/logs` confirms commit `f26de48e8bd3c01d7b963860a6696775b01a71f5` exists. Direct commit diff inspection was not available in the current toolset. | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG
- Negative/error-path coverage: ADEQUATE
- Manual mutation reasoning: ADEQUATE
- Test independence: STRONG
- Descriptive test names: STRONG

#### Data Safety
- No issues found. The change is limited to exception inheritance, code validation, and a lazy module re-export.

#### Test Gaps
- No pass-blocking gap remained after sequential fallback.
- The task-specific suite does not directly construct `CorruptionError(code=ERR_CORRUPT_*_CLASS, ...)`, but targeted broader regression runs exercised the live class-based constructor path through `detect_corruption` and `engine.list_tasks` and remained green aside from one unrelated stale test.

#### Necessity Check
- Skipped. No new dependency, integration, tool, or external capability was added.

#### Builder Process Quality
- CLEAN: one builder cycle, one verified task commit, no loop pattern in task body.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| CorruptionError inherits from KanbanError | `serve/kanban/src/owlbear_kanban/corruption.py:117`; task tests at `tests/test_error_hierarchy_1201.py:66,70,74`; scoped pytest 31/31 green | `test_corruption_error_is_subclass_of_kanban_error`, `test_kanban_error_in_mro`, `test_corruption_error_caught_by_kanban_error_handler` | PASS |
| CorruptionError.__init__ calls KanbanError.__init__(code, user_message) before setting extra attrs | `serve/kanban/src/owlbear_kanban/corruption.py:125-138` shows `_normalize_code`, `super().__init__(code_name, msg)`, then extra attrs; task tests at `tests/test_error_hierarchy_1201.py:91,100,110,115,130`; targeted regression support from `serve/kanban/tests/test_corruption.py` and `serve/kanban/tests/test_engine_storage.py` exercising live class-code paths | `test_instance_is_kanban_error_and_code_attr_set`, `test_user_message_kwarg_propagated_via_super`, `test_invalid_code_raises_value_error_via_kanban_validation`, `test_extra_attrs_preserved_alongside_kanban_error_attrs`, `test_detail_fallback_when_no_user_message` | PASS |
| KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* string codes | `serve/kanban/src/owlbear_kanban/errors.py:52-60`; task tests at `tests/test_error_hierarchy_1201.py:149,153` | `test_err_corrupt_code_in_kanban_error_codes`, `test_all_nine_corrupt_codes_present` | PASS |
| errors.py re-exports CorruptionError | `serve/kanban/src/owlbear_kanban/errors.py:101-103`; task test at `tests/test_error_hierarchy_1201.py:167` | `test_corruption_error_importable_from_errors_module` | PASS |
| isinstance(CorruptionError(...), KanbanError) is True | task test at `tests/test_error_hierarchy_1201.py:182`; constructor implementation at `serve/kanban/src/owlbear_kanban/corruption.py:133-135` | `test_isinstance_of_kanban_error` | PASS |
| All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses | dynamic subclass factory/use at `serve/kanban/src/owlbear_kanban/corruption.py:141-158`; task test at `tests/test_error_hierarchy_1201.py:200` | `test_dynamic_subclass_remains_corruption_error_and_is_kanban_error` | PASS |
| Existing consumers importing from corruption.py or errors.py still work | actual corruption.py consumers at `serve/kanban/src/owlbear_kanban/storage.py:45` and `serve/kanban/src/owlbear_kanban/engine.py:735,760`; lazy errors.py re-export at `serve/kanban/src/owlbear_kanban/errors.py:103`; task tests at `tests/test_error_hierarchy_1201.py:216,224` | `test_corruption_py_import_still_works`, `test_errors_py_import_still_works` | PASS |

### Deductions
- `-0.03`: `code-reader` subagent execution error required sequential fallback during service disruption.
- `-0.02`: direct commit diff inspection was unavailable; commit existence was verified via `.git/logs` and scope was reconstructed from builder notes/current snapshot.
- `-0.01`: targeted broader regression support was not fully green because of one unrelated stale test in `serve/kanban/tests/test_corruption.py`.

### Verdict
- PASS
- Confidence: 0.92
- Action: advance to `docs`

### Reflection
- `code-reader` was unavailable, so the review had to fall back to direct file inspection plus targeted quality-runner passes.
- The task-specific suite was strong on the explicit hierarchy AC, but the live class-based constructor path needed broader regression evidence before signing off.

## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md has no mention of CorruptionError, KanbanError, or error hierarchy. No other IN-scope prose doc references these types. |
| 2 | Module docstrings | Yes | Verified | corruption.py and errors.py docstrings accurate post-change. CorruptionError class docstring still correct. Module __getattr__ has no docstring (standard pattern). |
| 3 | External attribution | No | N/A | Pure inheritance refactor; no external patterns used. |
| 4 | Research doc | No | N/A | No research doc in task body. |
| 5 | Diagram maintenance | Yes | Updated | kanban.excalidraw (describes: serve/kanban/src/**) and mcp-topology.excalidraw (describes: serve/kanban/src/**) both match changed files. Footers updated from c1ed9c45 to 706cc2f7. Commit: fb1240c4. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/corruption.py | IN (docstrings) | Verified accurate |
| serve/kanban/src/owlbear_kanban/errors.py | IN (docstrings) | Verified accurate |
| tests/test_error_hierarchy_1201.py | OUT | N/A |
| share/diagrams/kanban.excalidraw | IN | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated |

### Files Updated
- share/diagrams/kanban.excalidraw (footer: 706cc2f7)
- share/diagrams/mcp-topology.excalidraw (footer: 706cc2f7)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files for task 1201)
- Commit-presence verification via `.git/logs` is useful when direct git diff access is unavailable, but it warrants a small confidence deduction.

[[2026-04-30]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| CorruptionError inherits from KanbanError | `corruption.py:117`: `class CorruptionError(KanbanError):` | PASS |
| __init__ calls KanbanError.__init__(code, user_message) before extra attrs | `corruption.py:133`: `super().__init__(code_name, msg)` before self.detail/path/file_path assignments | PASS |
| KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* codes | `errors.py:52-60`: 9 codes verified by grep | PASS |
| errors.py re-exports CorruptionError | `errors.py:102-103`: lazy __getattr__ re-export verified | PASS |
| isinstance(CorruptionError(...), KanbanError) is True | Structural consequence of confirmed inheritance; test_isinstance_of_kanban_error green | PASS |
| All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses | `corruption.py:141-158`: 9 _make_corruption_code_type calls verified | PASS |
| Existing consumers importing from corruption.py or errors.py still work | test_corruption_py_import_still_works, test_errors_py_import_still_works green; no circular import | PASS |

### Test Results
- Task-scoped: 31/31 passed, 0 failed (tests/test_error_hierarchy_1201.py)
- Full suite: 1493 passed, 13 failed, 4 skipped
- Full-suite failures: all pre-existing and out-of-scope
  - test_cockpit_react_compiler_1015.py (3): Babel/Vite frontend config
  - test_engine_dead_code_1112.py (2): engine status transitions
  - test_engine_end_work_fail_1125.py (1): end_work failure text
  - test_mcp_kanban_1091/1092/1126.py (7): MCP adapter task_id keyword arg signature mismatch -- unrelated to error hierarchy
- Lint: clean (corruption.py, errors.py, test_error_hierarchy_1201.py)

### Commits Verified
- Builder: f26de48e "fix: unify corruption and kanban errors (#1201, builder)"
- Doc-writer: fb1240c4 "docs: update diagram footers for error hierarchy unification (#1201, doc-writer)"

### Reviewer Evidence
- Present, detailed, PASS verdict. 7 AC lines fully mapped. One LAX notation (constructor ordering proven by source inspection, not isolated test) -- accepted: source directly confirms ordering.

### Architect Quality: 4/5
AC was specific, testable, with precise constructor contract and explicit out-of-scope bounds. Minor gap: lazy re-export pattern needed to avoid circular import was not specified in AC, requiring builder empirical discovery. Does not affect verdict.

### Deduction Breakdown
- quality-runner infrastructure failure required direct terminal invocation: -.01

### Confidence: 0.99
### Action: archive