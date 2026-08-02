---
id: 1202
title: Narrow exception handling (BLE001) in engine.py
status: archived
priority: medium
created: 2026-04-30 15:28:57.610272+00:00
updated: 2026-05-01T13:46:58.532157+00:00
tags:
- audit-kanban
- safety
parent:
depends_on:
- 1203
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace broad `except Exception` (BLE001) with specific exception types at each of the 5 BLE001 sites in engine.py.

**Note:** `_move_file` (line 370) already has correct narrow handling (`FileNotFoundError, subprocess.TimeoutExpired`) — do not modify it. The task body originally listed `_move_file` as a target; that was inaccurate. `yaml.YAMLError` and `subprocess.CalledProcessError` are not applicable at any of the 5 real violation sites.

## Sites and Target Exception Types

| Line | Function | Current | Target |
|------|----------|---------|--------|
| 697 | `list_tasks` (archive scan) | `except Exception:` | `except CorruptionError:` |
| 733 | `list_tasks` (main task scan) | `except Exception as _exc:` + isinstance check | `except CorruptionError:` — remove isinstance check; both branches do `continue` |
| 1589 | `release_expired_claims` | `except Exception:` | `except (FileNotFoundError, ValueError, KeyError, CorruptionError):` |
| 1676 | quarantine repair (`create_task` call) | `except Exception as _exc:` | `except (ValueError, KanbanError, OSError):` |
| 2342 | `pick_tasks` (`resolve_pending_drs` call) | single `except Exception` for both import + call | split: `except ImportError` for import; `except (KanbanError, OSError, ValueError)` for the `resolve_pending_drs()` call |

## Restructuring Pattern for Line 2342

```python
try:
    decisions = importlib.import_module("owlbear_kanban.decisions")
except ImportError as exc:
    LOGGER.warning("Failed to import decisions module before pick_tasks: %s", exc)
else:
    try:
        decisions.resolve_pending_drs(self.engine)
    except (KanbanError, OSError, ValueError) as exc:
        LOGGER.warning("Failed to resolve pending DRs before pick_tasks: %s", exc)
```

## AC
- [ ] Line 697 (`list_tasks` archive scan): `except CorruptionError:` replaces `except Exception:` (td:2)
- [ ] Line 733 (`list_tasks` main scan): `except CorruptionError:` replaces `except Exception as _exc:`; redundant `isinstance` check and duplicate `continue` removed (td:2)
- [ ] Line 1589 (`release_expired_claims`): `except (FileNotFoundError, ValueError, KeyError, CorruptionError):` replaces `except Exception:` (td:2)
- [ ] Line 1676 (quarantine repair): `except (ValueError, KanbanError, OSError):` replaces `except Exception as _exc:` (td:2)
- [ ] Line 2342 (`pick_tasks`): try-block restructured per pattern above — `except ImportError` for import failure; `except (KanbanError, OSError, ValueError)` for `resolve_pending_drs` failures; both branches log at WARNING level (td:2)
- [ ] No `# noqa: BLE001` suppressions remain in engine.py (td:1)
- [ ] `ruff check serve/kanban` exits clean (td:1)
- [ ] All existing tests pass (td:0)

## Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| list_tasks archive scan (line 697) | `read_task` raises unexpected type | Not in `(FileNotFoundError, ValueError, KeyError, CorruptionError)` | No — propagates | `list_tasks` fails for caller |
| list_tasks main scan (line 733) | Same | Same | No — propagates | Same |
| release_expired_claims (line 1589) | `read_task` raises unexpected type | Not in catch tuple | No — propagates | Loop breaks early |
| quarantine repair (line 1676) | `create_task` raises unexpected type | Not `ValueError, KanbanError, OSError` | No — propagates | `RepairOutcome` not appended; repair aborts |
| pick_tasks (line 2342) | `resolve_pending_drs` raises unexpected type | Not in catch tuple | No — propagates | `pick_tasks` fails |

**Builder pre-check:** Verify `read_task` raises only `(FileNotFoundError, ValueError, KeyError, CorruptionError)` across all codepaths before finalizing lines 697/733/1589 tuples. If `read_task` raises additional types, expand the tuple accordingly and note in commit message.

## Finding: 4.1

## Architecture Review

**Verdict:** REFINE → APPROVE — AC rewritten with site-specific exception types. Advancing to `todo`.

### AC Assessment

| AC line | Assessment | Action |
|---------|------------|--------|
| "No bare `except Exception` in engine.py" | Ambiguous — includes aliased forms (`except Exception as _exc`); Ruff BLE001 covers both but AC was misleading | Replaced with site-specific AC lines |
| "Each handler catches the narrowest applicable exception" | Not verifiable — no per-site types specified; task body suggested `yaml.YAMLError` and `subprocess.CalledProcessError` which don't apply to any real violation site | Replaced with per-site exception tuples |
| "Ruff BLE001 clean" | Verifiable; redundant with line 1 | Retained as explicit CI gate |
| "Existing tests pass" | Verifiable (td:0) | Retained |

### Architecture Notes

- `_move_file` is NOT a BLE001 violation site. It already uses `except (FileNotFoundError, subprocess.TimeoutExpired)`. Original task body was incorrect.
- `yaml.YAMLError` and `subprocess.CalledProcessError` are not relevant to any of the 5 real sites; they were removed from the approach.
- Line 733: the existing `isinstance(_exc, _CorruptionError)` check (with lazy import) confirms `CorruptionError` is the only intended catch at that site; both branches do `continue`. Narrowing to `except CorruptionError:` removes the dead isinstance logic.
- Line 2342: `resolve_pending_drs` mixes import error with runtime error in one block. Restructuring with `try/except ImportError / else / try/except tuple` is architecturally correct.
- **Risk:** Any site where narrowing drops an exception type that `read_task` actually raises in production will convert a silent skip into a propagated crash. The builder pre-check on `read_task`'s actual raise surface is mandatory.

### Dependency Analysis
- Depends on #1203 ("Fix empty-title error code in AgentView.create_task") — archived (complete). Dependency satisfied.

### Challenger
Not dispatched (REFINE verdict; AC was fully rewritten by architect).

[[2026-04-30]]
## Architecture Review

**Verdict:** REFINE → APPROVE — AC rewritten with per-site exception types. Advancing to todo.

AC was too vague to guide the builder: "each handler catches the narrowest applicable exception" with no per-site types. Additionally, the original task body incorrectly listed `_move_file` as a violation site (it already has correct narrow handling) and suggested `yaml.YAMLError` / `subprocess.CalledProcessError` which don't apply to any real BLE001 site.

5 real sites identified: lines 697, 733 (list_tasks), 1589 (release_expired_claims), 1676 (quarantine repair create_task), 2342 (pick_tasks). Per-site exception types and restructuring pattern for line 2342 are now specified in the task body. Failure mode map included. Builder pre-check on read_task raise surface is mandatory before finalizing tuples at lines 697/733/1589.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_engine_ble001_1202.py
- Classes: TestFromAC_ListTasksArchiveScanExceptions, TestFromAC_ListTasksMainScanExceptions, TestFromAC_SweepExceptions, TestFromAC_RepairStorageExceptions, TestFromAC_PickTasksImportRestructuring, TestFromAC_NoBleSuppressions, TestFromAC_RuffClean
- Tests per category: happy 0, edge 2, error 8, boundary 3
- Total: 13 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 line 697 archive scan (td:2) | test_archive_scan_non_narrowed_exception_propagates (error), test_archive_scan_attribute_error_propagates (boundary) |
| AC2 line 733 main scan (td:2) | test_main_scan_non_narrowed_exception_propagates (error), test_main_scan_oserror_propagates (boundary) |
| AC3 line 1589 sweep (td:2) | test_sweep_non_narrowed_exception_propagates (error), test_sweep_oserror_propagates (boundary — PermissionError, OSError subclass not FileNotFoundError) |
| AC4 line 1676 repair_storage (td:2) | test_repair_storage_runtime_error_from_create_task_propagates (error), test_repair_storage_type_error_from_create_task_propagates (boundary) |
| AC5 line 2342 pick_tasks (td:2) | test_pick_tasks_import_runtime_error_propagates (error), test_pick_tasks_resolve_pending_drs_import_error_propagates (edge), test_pick_tasks_resolve_pending_drs_runtime_error_propagates (boundary) |
| AC6 no noqa BLE001 (td:1) | test_engine_py_has_no_ble001_noqa |
| AC7 ruff clean (td:1) | test_ruff_ble001_check_passes (uses --ignore-noqa flag) |
| AC8 existing tests pass (td:0) | skipped — td:0 |

Strategy: All RED tests verify that exceptions currently swallowed by broad `except Exception:` propagate after narrowing. Using `DID NOT RAISE` failures as RED signal. Mock targets: `owlbear_kanban.engine.read_task`, `owlbear_kanban.storage.detect_corruption`, `owlbear_kanban.corruption.scan_and_fix`, `KanbanEngine.create_task`, `importlib.import_module`.
[[2026-04-30]]
## Builder Notes
- Implementation: narrowed all 5 targeted BLE001 handlers in serve/kanban/src/owlbear_kanban/engine.py per AC1-AC6.
- RED verification (quality-runner): 13/13 TestFromAC failed before implementation.
- Post-implementation verification (quality-runner): 12/13 TestFromAC pass; remaining failure is AC7 (`TestFromAC_RuffClean::test_ruff_ble001_check_passes`).
- Lint (scoped): clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_engine_ble001_1202.py.
- Coverage (scoped run): engine module measured; task blocked by AC mismatch before GREEN completion.

Evidence summary:
- Remaining failing assertion runs `uv run ruff check serve/kanban --select BLE001 --ignore-noqa` and expects exit 0.
- The failure reports pre-existing BLE001 violations in unrelated modules (activity_store.py, corruption.py, decisions.py, migrate.py, etc.), outside this task's objective/scope (objective is 5 sites in engine.py).
- Therefore AC7 currently encodes package-wide cleanup not implied by AC1-AC6/objective and is infeasible as a surgical builder task without broad cross-module refactor.

Requested AC refinement:
- Either (A) scope AC7/test to engine-only BLE001 check, or (B) split package-wide BLE001 cleanup into a separate backlog task with explicit file list and acceptance criteria.

Post-task reflection:
- Problem faced: task-scoped fix versus package-wide BLE001 gate mismatch.
- Workaround applied: completed all engine.py-targeted narrowing first, then validated via quality-runner to isolate residual failure to AC7 only.
- Pattern discovered: using `--ignore-noqa` on package path can pull in pre-existing debt unrelated to a narrowly scoped task.
- Quality gap: AC7 should be aligned with objective scope or explicitly expanded with planned decomposition.

## AC7 Correction (Architect Re-review)

AC7 refined to engine-scope only. Replace:

> `ruff check serve/kanban` exits clean (td:1)

With:

> `ruff check serve/kanban/src/owlbear_kanban/engine.py --select BLE001` exits clean (td:1)

**Rationale:** The task objective is 5 BLE001 sites in engine.py. Package-wide BLE001 cleanup in activity_store.py, corruption.py, decisions.py, migrate.py is pre-existing debt outside this task's scope. Checking the whole package via `_SERVE_KANBAN` pulls in those violations; scoping to `_ENGINE_PY` is correct.

**Test update required:** `TestFromAC_RuffClean::test_ruff_ble001_check_passes` — change `str(_SERVE_KANBAN)` → `str(_ENGINE_PY)` in the subprocess args. No other changes needed; engine.py BLE001 violations are already resolved per builder notes (12/13 pass).

[[2026-04-30]]
## Architecture Review

**Verdict:** REFINE → APPROVE — AC7 scoped to engine.py. Advancing to `todo`.

### Context

Builder returned task to backlog after completing all 5 BLE001 narrowing changes in engine.py (12/13 TestFromAC pass). Sole blocker: `TestFromAC_RuffClean::test_ruff_ble001_check_passes` runs `ruff check serve/kanban --select BLE001 --ignore-noqa` (package-wide), which pulls in pre-existing BLE001 violations in activity_store.py, corruption.py, decisions.py, migrate.py — all outside this task's scope.

### AC Assessment

| AC line | Assessment | Action |
|---------|------------|--------|
| AC1-AC5 (site-specific narrowing) | Verified by 10/10 tests passing | No change |
| AC6 (no noqa: BLE001 in engine.py) | Verifiable, engine-scoped (td:1) | No change |
| AC7 `ruff check serve/kanban` exits clean (td:1) | Scope too wide — catches pre-existing debt in unrelated modules | **Refined** to `ruff check serve/kanban/src/owlbear_kanban/engine.py --select BLE001` exits clean (td:1) |
| AC8 existing tests pass (td:0) | No change | No change |

### Architecture Notes

- Builder's Option A is architecturally correct. Package-wide BLE001 cleanup (activity_store.py, corruption.py, decisions.py, migrate.py) is separate scope; add a follow-up `audit-kanban` task if desired.
- No new failure modes introduced by AC refinement — narrower scope means the test will pass once `_SERVE_KANBAN` → `_ENGINE_PY` substitution is made in the test.
- The `--ignore-noqa` flag in the test remains appropriate (forces ruff to report actual violations regardless of suppression comments).

### Dependency Analysis

- Depends on #1203 (archived/done). Satisfied.

### Design Diverge

Skipped — single approach (narrow scope to engine.py). No competing approaches with split criteria.

### Challenge Results

- Challenger: SKIPPED — REFINE verdict (AC correction only, no design decision to challenge).

### Test Depth

- Max depth: td:2
- Test-writer: PROCEED — update `test_ruff_ble001_check_passes` to use `_ENGINE_PY` instead of `_SERVE_KANBAN` in subprocess args.

### Verdict: REFINE → APPROVE

AC7 narrowed to engine.py scope. Test-writer to update the one failing test. Builder has already implemented all 5 BLE001 narrowing changes; this cycle completes the task.
[[2026-04-30]]
## Test-Writer Notes
- Retry: updated `TestFromAC_RuffClean::test_ruff_ble001_check_passes` — changed `str(_SERVE_KANBAN)` → `str(_ENGINE_PY)` per AC7 refinement (engine.py scope only, not package-wide).
- Updated module docstring and class/method docstrings to reflect narrowed scope.
- Builder skip: test-only retry — all 13 tests pass against current implementation (builder already narrowed all 5 BLE001 sites in engine.py).
- ruff: clean
[[2026-04-30]]
## Builder Notes
- Implementation status: verified all AC-targeted exception handlers in serve/kanban/src/owlbear_kanban/engine.py now use narrow catches (list_tasks archive/main scans, sweep, repair_storage, pick_tasks import/call split).
- Code changes in this pass: no additional net diff to commit (working tree for serve/kanban/src/owlbear_kanban/engine.py is clean).
- Tests (quality-runner scoped): 13/13 passed in tests/test_engine_ble001_1202.py; failed: 0.
- Expanded verification (quality-runner): 59/59 passed across tests/test_engine_ble001_1202.py, tests/test_engine_coverage.py, tests/test_engine_coverage_1113.py.
- Lint (quality-runner scoped): ruff clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_engine_ble001_1202.py.
- Coverage evidence: owlbear_kanban.engine measured at 21% in scoped coverage runs (module-wide denominator; task AC does not require module-wide 90%).

Evidence summary:
- AC1-AC5 behavior verified by propagation tests in TestFromAC_* suites (all green).
- AC6 verified: no '# noqa: BLE001' remains in engine.py.
- AC7 verified: BLE001 check on engine.py scope passes.

Post-task reflection:
- Problem faced: initial scoped quality run returned full RED despite task history indicating prior GREEN.
- Workaround applied: revalidated from current snapshot with scoped and expanded quality-runner passes until stable green evidence was produced.
- Pattern discovered: task history can lag current code reality; only live quality-runner output should gate release.
- Quality gap: module-wide coverage percentage is not a reliable gate for narrow exception-handling tasks in very large modules.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped: 13 passed, 0 failed, 0 skipped in tests/test_engine_ble001_1202.py
- quality-runner broader regression spotcheck: 75 passed, 1 failed, 0 skipped across tests/test_pick_tasks_resolve.py and tests/test_engine_cockpit_view_1078.py
- failing existing test: tests/test_pick_tasks_resolve.py::TestFromAC_PickTasksResolveIntegration::test_resolve_exceptions_do_not_propagate -> RuntimeError: DR resolve failed

### Lint
- clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_engine_ble001_1202.py

### Coverage
- scoped report: owlbear_kanban.engine 17%, overall 21%
- informational only: module-wide denominator on a very large file; not used as a gate here

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage / AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC1 archive scan narrows to CorruptionError | engine.py:696 is correct, but tests/test_engine_ble001_1202.py:120 and :132 only assert RuntimeError/AttributeError propagation; they would still pass if the CorruptionError catch were removed | FAIL |
| AC2 main scan narrows to CorruptionError | engine.py:732 is correct, but tests/test_engine_ble001_1202.py:163 and :180 only assert RuntimeError/OSError propagation; no CorruptionError continue-path proof | FAIL |
| AC3 sweep narrows to (FileNotFoundError, ValueError, KeyError, CorruptionError) | engine.py:1583 is correct, but tests/test_engine_ble001_1202.py:206 and :223 only assert RuntimeError/PermissionError propagation; no caught-tuple proof | FAIL |
| AC4 repair_storage narrows to (ValueError, KanbanError, OSError) | engine.py:1670 is correct, but tests/test_engine_ble001_1202.py:259 and :277 only assert RuntimeError/TypeError propagation; no ValueError/KanbanError/OSError failed-RepairOutcome proof | FAIL |
| AC5 pick_tasks split import/call handling with WARNING logs | engine.py:2327-2333 matches AC, but tests/test_engine_ble001_1202.py:303, :325, and :343 do not cover import-time ImportError or caught KanbanError/OSError/ValueError branches and never assert the WARNING logs at engine.py:2328 and :2333. Broader spotcheck also fails tests/test_pick_tasks_resolve.py:152 because that durable suite still expects RuntimeError from resolve_pending_drs to be swallowed | FAIL |
| AC6 no BLE001 suppressions remain in engine.py | tests/test_engine_ble001_1202.py:363 directly scans for the forbidden token; grep found no BLE001 suppression in engine.py | PASS |
| AC7 Ruff BLE001 check on engine.py exits clean | tests/test_engine_ble001_1202.py:400 asserts exit code 0; quality-runner ruff exit code was 0 | PASS |
| AC8 all existing tests pass | Broader quality-runner spotcheck found 1 failing existing test: tests/test_pick_tasks_resolve.py::TestFromAC_PickTasksResolveIntegration::test_resolve_exceptions_do_not_propagate | FAIL |

#### Security Review
- No issues found. The changes are limited to exception narrowing and WARNING logs.

#### Test Integrity
- No weakened or removed TestFromAC assertions detected in the current snapshot.

#### Test Quality
- WEAK. AC1-AC5 tests prove only that unexpected exceptions now propagate. They do not prove that the newly allowed catch branches are still handled, and AC5 does not prove either WARNING log path.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gaps
- Missing CorruptionError continue-path tests for list_tasks archive and main scans.
- Missing caught-tuple tests for sweep.
- Missing caught-tuple tests for repair_storage that assert the failed RepairOutcome path.
- Missing pick_tasks warning-path tests for import-time ImportError and caught KanbanError/OSError/ValueError from resolve_pending_drs.
- Existing durable pick_tasks suite at tests/test_pick_tasks_resolve.py is stale relative to the refined AC5 contract.

#### Builder Process Quality
- CLEAN. Two Builder Notes sections, but they represent implementation then live revalidation after AC7 refinement, not repeated identical retries.

### Deductions
- -0.08 AC1 proof gap
- -0.08 AC2 proof gap
- -0.08 AC3 proof gap
- -0.08 AC4 proof gap
- -0.12 AC5 proof gap plus stale durable-suite failure
- -0.10 AC8 existing-suite failure
- Confidence: 0.66

### Verdict
- FAIL -> todo
- Reason: implementation appears aligned to the refined AC, but the task-owned tests are lax for AC1-AC5 and an existing durable pick_tasks suite is still red under the new contract.

### Required Follow-up
1. Update tests/test_pick_tasks_resolve.py:152 so unexpected RuntimeError from resolve_pending_drs is expected to propagate, and add explicit proof for the caught ImportError/KanbanError/OSError/ValueError warning paths.
2. Strengthen tests/test_engine_ble001_1202.py so AC1-AC4 exercise the allowed catch branches, not only unexpected-exception propagation.
3. Add explicit WARNING-log assertions for both AC5 branches at engine.py:2328 and :2333.
4. Re-run the task suite plus affected existing suites before returning to review.
[[2026-05-01]]
## Test-Writer Notes
- Retry: filled all reviewer gaps. All new tests PASS against current implementation (builder skip per Step 1b.1).
- Files: tests/test_engine_ble001_1202.py, tests/test_pick_tasks_resolve_1184.py

### Changes
- **tests/test_pick_tasks_resolve_1184.py**: Updated `test_resolve_exceptions_do_not_propagate` — was asserting RuntimeError does NOT propagate (old broad-except contract); now asserts RuntimeError DOES propagate (narrowed `except (KanbanError, OSError, ValueError)` contract per AC5).
- **tests/test_engine_ble001_1202.py**: Added imports (`logging`, `CorruptionError`, `KanbanError`, `PickTasksResponse`). Added 5 new test classes:
  - `TestFromAC_ListTasksArchiveScanCatchBranch` (AC1 catch-branch, 1 test): CorruptionError caught in archive scan → list_tasks returns normally.
  - `TestFromAC_ListTasksMainScanCatchBranch` (AC2 catch-branch, 1 test): CorruptionError caught in main scan → list_tasks returns normally.
  - `TestFromAC_SweepCatchBranch` (AC3 catch-branch, 4 tests): FileNotFoundError/ValueError/KeyError/CorruptionError each caught in sweep → returns [].
  - `TestFromAC_RepairStorageCatchBranch` (AC4 catch-branch, 3 tests): ValueError/KanbanError/OSError from create_task → failed RepairOutcome appended (not propagated).
  - `TestFromAC_PickTasksWarningLogs` (AC5 warning-log, 4 tests): ImportError from import → caught + WARNING logged; KanbanError/OSError/ValueError from resolve_pending_drs → caught + WARNING logged.

### Test counts
- Existing (preserved): 13 tests
- New: 14 tests (1+1+4+3+4 catch-branch/warning-log + 1 updated in test_pick_tasks_resolve_1184.py)
- Total: 31 tests, all PASS

### AC coverage
| AC | Tests |
|----|-------|
| AC1 catch-branch | test_archive_scan_corruption_error_is_caught |
| AC2 catch-branch | test_main_scan_corruption_error_is_caught |
| AC3 catch-branch | test_sweep_file_not_found/value/key/corruption_error_is_caught (×4) |
| AC4 catch-branch | test_repair_storage_value/kanban/oserror_creates_failed_outcome (×3) |
| AC5 warning-log | test_pick_tasks_import_error/kanban/os/value_error_*_logged (×4) |
| AC5 propagation fix | test_resolve_exceptions_do_not_propagate updated to expect propagation |
| ruff | clean |
[[2026-05-01]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) to remove in-function duplicate-ID imports and raise the already top-level-imported `CorruptionError` with `ERR_CORRUPT_DUPLICATE_ID`.
- Scope: surgical lint-fix only; no behavioral change to AC-targeted BLE001 narrowing logic.
- Tests: 31 passed, 0 failed, 0 skipped (`tests/test_engine_ble001_1202.py`, `tests/test_pick_tasks_resolve_1184.py`).
- Lint: clean (`ruff check` on `serve/kanban/src/owlbear_kanban/engine.py` and both task test files).
- Coverage: `owlbear_kanban.engine` 25% in scoped run (module is very large; coverage figure is informational for this narrow fix).
- Commit: `252ad283` with only [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py).

Evidence summary:
- quality-runner scoped gate now returns pytest exit 0 and ruff exit 0 for task-owned scope.
- Task acceptance lines around narrow exception handling remain satisfied; this pass resolved a remaining lint regression (PLC0415/RUF100 then I001) introduced by import locality.

Post-task reflection:
- Problem faced: prior task snapshot was mostly green but still had live lint regressions in `engine.py`.
- Workaround applied: moved duplicate-ID symbol import to module top-level and removed now-unneeded local/noqa pattern.
- Pattern discovered: local import hotfixes can satisfy one rule while causing `PLC0415`/`RUF100` churn; prefer stable top-level imports when import-cycle risk is absent.
- Quality gap: task-scoped coverage percentage on monolithic modules is a weak quality signal for narrowly targeted maintenance changes.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped: 31 passed, 0 failed, 0 skipped in [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py) and [tests/test_pick_tasks_resolve_1184.py](tests/test_pick_tasks_resolve_1184.py)
- quality-runner related-suite spotcheck: 28 passed, 0 failed, 0 skipped in [tests/test_engine_coverage.py](tests/test_engine_coverage.py) and [tests/test_pick_tasks_resolve_1184.py](tests/test_pick_tasks_resolve_1184.py)
- quality-runner full regression: 3413 passed, 125 failed, 4 skipped; representative unrelated baseline failures include [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), [tests/test_frontend_polling_1227.py](tests/test_frontend_polling_1227.py), and [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py)

### Lint
- scoped lint: clean for [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py), and [tests/test_pick_tasks_resolve_1184.py](tests/test_pick_tasks_resolve_1184.py)
- full-repo lint baseline: 4 unrelated violations outside task scope

### Coverage
- scoped coverage: `owlbear_kanban.engine` 25% (informational only; monolithic-module denominator)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage / AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC1 archive scan narrows to `CorruptionError` | handler at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L694); propagation proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L116) and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L137); catch-branch proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L382) | PASS |
| AC2 main scan narrows to `CorruptionError` | handler at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L730); propagation proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L165) and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L184); catch-branch proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L412) | PASS |
| AC3 sweep narrows to `(FileNotFoundError, ValueError, KeyError, CorruptionError)` | handler at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1585); propagation proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L210) and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L229); catch-branch proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L441), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L455), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L469), and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L483) | PASS |
| AC4 repair-storage narrows to `(ValueError, KanbanError, OSError)` | handler at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1672); propagation proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L267) and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L287); catch-branch proof at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L515), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L541), and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L561) | PASS |
| AC5 pick_tasks split handlers and WARNING logs | split import/call paths at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2353) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2360); WARNING calls at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2355) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2362); propagation proof exists at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L319), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L333), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L355), and [tests/test_pick_tasks_resolve_1184.py](tests/test_pick_tasks_resolve_1184.py#L164). But the warning-path tests [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L590), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L615), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L637), and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L659) only assert response type at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L605), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L629), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L651), and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L673), and accept any log level `>= WARNING` at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L609), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L631), [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L653), and [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L675). An implementation that logs at `ERROR` or returns early before [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2366) would still pass. | FAIL |
| AC6 no `# noqa: BLE001` suppressions remain | no suppression found in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py); direct scanner test at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L690) | PASS |
| AC7 Ruff BLE001 check on engine.py exits clean | direct subprocess assertion at [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py#L709); scoped quality-runner ruff exit code 0 | PASS |
| AC8 all existing tests pass | full regression is globally red: 3413 passed, 125 failed, 4 skipped; full lint baseline has 4 unrelated violations. This gate is infeasible as written for task 1202 and cannot be honestly certified from the live workspace snapshot. | FAIL |

#### Security Review
- No issues found. The production changes stay within exception narrowing and warning logging.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected.

#### Test Quality
- WEAK. AC5 warning-path proof does not assert exact `WARNING` severity and does not prove execution continues into task selection after logging.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gaps
- AC5 needs exact-level log assertions and a post-log continuation proof tied to [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2366).
- AC8 needs architectural rework: the repo baseline is globally red, so a task-scoped engine cleanup cannot satisfy a literal global-green gate.

#### Builder Process Quality
- CLEAN. The live implementation matches AC1-AC7. Remaining issues are proof quality and AC design, not a source-code miss.

### Deductions
- -0.08 AC5 exact-warning-level proof gap
- -0.06 AC5 continuation-after-log proof gap
- -0.14 AC8 global-red baseline makes the gate infeasible as written
- Confidence: 0.72

### Verdict
- FAIL -> backlog
- Reason: implementation is aligned to the narrowed handlers, but AC5 is still only partially proved and AC8 is structurally infeasible against the current workspace baseline.
- Routing note: this task already contained one prior `## Review Evidence` failure section, so this is a second review fail and routes to `backlog` per reviewer loop-breaker rules.

### Required Follow-up
1. Strengthen the AC5 warning-path tests in [tests/test_engine_ble001_1202.py](tests/test_engine_ble001_1202.py) to assert exact `WARNING` level and prove the flow reaches [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2366) after each caught branch.
2. Rework or split AC8. A task-scoped engine exception cleanup cannot honestly satisfy a literal global-green repo gate while the workspace baseline remains 125 tests and 4 lint violations red outside this task.
3. Optional clarity cleanup: rename [tests/test_pick_tasks_resolve_1184.py](tests/test_pick_tasks_resolve_1184.py#L164) so the test name matches its propagation assertion.
[[2026-05-01]]

## AC8 Correction (Architect Re-review)

AC8 refined to task-scoped regression gate. Replace:

> All existing tests pass (td:0)

With:

> No regressions in engine-related test suites (`tests/test_engine_coverage.py`, `tests/test_pick_tasks_resolve_1184.py` pass alongside task-owned suite) (td:0)

**Rationale:** The workspace baseline has 125+ failing tests and 4 lint violations from pre-existing debt outside this task's scope. A literal "all existing tests pass" gate is structurally infeasible for any task-scoped engine change. The corrected gate verifies no regressions in adjacent engine test suites — the meaningful gate for this narrow exception-handling cleanup.

**AC5 warning-level precision (reviewer concern addressed):** The `r.levelno >= logging.WARNING` filter is standard caplog practice and adequate for this AC. The AC says "log at WARNING level"; implementation uses `LOGGER.warning()`. The `isinstance(result, PickTasksResponse)` assertion proves continuation — `pick_tasks()` returns `PickTasksResponse` only after execution reaches `list_tasks()` (line 2366) and the subsequent wave-building logic. No early-return path exists between the DR resolution block and `list_tasks()`. No additional test cycle required.

[[2026-05-01]]
## Architecture Review

**Verdict:** REFINE → APPROVE — AC8 scoped to task-relevant regression gate. Advancing to `todo`.

### Context

Task returned to backlog after second review failure. Two issues: (1) AC5 warning-path test precision, (2) AC8 "all existing tests pass" structurally infeasible against globally-red workspace baseline.

### AC Assessment

| AC line | Assessment | Action |
|---------|------------|--------|
| AC1-AC4 (site-specific narrowing) | Implementation verified at engine.py lines 694, 730, 1585, 1672. Tests cover both propagation and catch-branch paths (PASS in second review). | No change |
| AC5 (pick_tasks split + WARNING logs) | Implementation correct at engine.py lines 2353-2363. Reviewer flagged `>= WARNING` filter and lack of continuation proof. **Rebuttal:** `>= WARNING` is standard caplog practice; AC says "log at WARNING level" and implementation uses `LOGGER.warning()`. `isinstance(result, PickTasksResponse)` IS continuation proof — no early-return path exists between DR resolution block and `list_tasks()` at line 2366. | No change — reviewer concern addressed in body |
| AC6 (no noqa: BLE001) | Verified, engine-scoped (td:1) | No change |
| AC7 (ruff BLE001 on engine.py) | Already refined to engine.py scope in prior cycle | No change |
| AC8 "All existing tests pass" (td:0) | Structurally infeasible — workspace baseline 125 failures, 4 lint violations from pre-existing debt | **Refined** to task-scoped regression gate: engine-related suites (`tests/test_engine_coverage.py`, `tests/test_pick_tasks_resolve_1184.py`) pass alongside task-owned suite |

### Architecture Notes

- All 5 BLE001 sites in engine.py confirmed narrowed to correct exception types.
- `_move_file` (line 370) correctly excluded — already has narrow handling.
- Line 2342 restructured with `try/except ImportError/else/try/except tuple` pattern — verified in source.
- AC8 global-green gate was a recurring pipeline blocker across two review cycles. Scoping to engine-adjacent suites resolves the infeasibility without reducing meaningful regression detection.

### Dependency Analysis

- Depends on #1203 (archived/done). Satisfied.

### Design Diverge

Skipped — single approach (AC text correction only).

### Challenge Results

Challenger: SKIPPED — REFINE verdict (narrow AC8 text correction, no design decision). Design was validated in original architecture review cycle.

### Test Depth

- Max depth: td:2
- Test-writer: update `test_ruff_ble001_check_passes` scope per AC8 correction (engine-adjacent suite gate, not global).
[[2026-05-01]]
## Test-Writer Notes
- Retry (3rd cycle): test-only cleanup. All 31 existing tests pass against current implementation — direct-to-review advance per Step 1b.1.
- Files: tests/test_engine_ble001_1202.py (unchanged), tests/test_pick_tasks_resolve_1184.py (test rename only)

### Changes
- **tests/test_pick_tasks_resolve_1184.py**: Renamed `test_resolve_exceptions_do_not_propagate` → `test_unexpected_exception_from_resolve_propagates` per reviewer's optional clarity suggestion. Name now matches the assertion (RuntimeError from resolve_pending_drs propagates under narrowed except tuple).
- No new tests written. Architect rebutted both reviewer concerns:
  - AC5 `>= WARNING` filter and `isinstance(result, PickTasksResponse)` assertion are adequate (standard caplog practice; PickTasksResponse return IS continuation proof).
  - AC8 refined to td:0 (task-scoped regression gate, no test needed).

### Verification
- pytest: 31 passed, 0 failed (tests/test_engine_ble001_1202.py + tests/test_pick_tasks_resolve_1184.py)
- ruff: clean for both test files
- Commit: 7de75b65

### AC coverage (unchanged from prior cycle — all PASS)
| AC | Tests |
|----|-------|
| AC1 archive scan propagation + catch-branch | 3 tests |
| AC2 main scan propagation + catch-branch | 3 tests |
| AC3 sweep propagation + catch-branch (×4) | 6 tests |
| AC4 repair_storage propagation + catch-branch (×3) | 5 tests |
| AC5 pick_tasks propagation (×3) + warning-log (×4) | 7 tests |
| AC6 no noqa: BLE001 | 1 test |
| AC7 ruff BLE001 engine.py | 1 test |
| AC8 td:0 | skipped |
| Total | 26 tests in 1202 + 5 in 1184 = 31 |

Builder skip: test-only retry, all 31 tests green against current implementation.
[[2026-05-01]]
## Builder Notes
- Implementation status: no additional code changes required in this pass; prior builder commits already satisfy the narrowed exception-handling AC in `serve/kanban/src/owlbear_kanban/engine.py`.
- Verification (quality-runner, scoped): 54 passed, 0 failed, 0 skipped across `tests/test_engine_ble001_1202.py`, `tests/test_pick_tasks_resolve_1184.py`, and `tests/test_engine_coverage.py`.
- Lint (quality-runner scoped): clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_ble001_1202.py`, and `tests/test_pick_tasks_resolve_1184.py`.
- Coverage: `owlbear_kanban.engine` measured at 29% in scoped run (informational for this narrow maintenance task in a monolithic module).

Evidence summary:
- AC-targeted exception narrowing behavior remains green under live scoped verification.
- Engine-related regression gate is green (`tests/test_engine_coverage.py` + task-owned suites).
- No new regressions introduced in this builder cycle.

Post-task reflection:
- Problem faced: task had long history with mixed prior review outcomes; needed fresh live verification from current snapshot.
- Workaround applied: re-ran quality-runner on the exact refined gate scope instead of trusting historical notes.
- Pattern discovered: for mature tasks with multiple retries, current quality-runner output should be treated as the authoritative release signal.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped: 54 passed, 0 failed, 0 skipped across tests/test_engine_ble001_1202.py, tests/test_pick_tasks_resolve_1184.py, and tests/test_engine_coverage.py

### Lint
- clean for serve/kanban/src/owlbear_kanban/engine.py, tests/test_engine_ble001_1202.py, and tests/test_pick_tasks_resolve_1184.py

### Coverage
- owlbear_kanban.engine: 29% module coverage in the scoped run
- informational only for this narrow maintenance task in a monolithic module

### Pass 1 - CRITICAL
#### AC Compliance
- AC1 PASS: archive scan now catches CorruptionError at serve/kanban/src/owlbear_kanban/engine.py:694; propagation tests and catch-branch test in tests/test_engine_ble001_1202.py cover both sides
- AC2 PASS: main scan now catches CorruptionError at serve/kanban/src/owlbear_kanban/engine.py:730; propagation tests and catch-branch test in tests/test_engine_ble001_1202.py cover both sides
- AC3 PASS: sweep now catches only (FileNotFoundError, ValueError, KeyError, CorruptionError) at serve/kanban/src/owlbear_kanban/engine.py:1585; propagation and caught-tuple tests cover the contract
- AC4 PASS: repair_storage now catches only (ValueError, KanbanError, OSError) at serve/kanban/src/owlbear_kanban/engine.py:1672; propagation tests and failed-RepairOutcome tests cover the contract
- AC5 FAIL: source uses LOGGER.warning at serve/kanban/src/owlbear_kanban/engine.py:2355 and serve/kanban/src/owlbear_kanban/engine.py:2362, but the four warning-path tests only assert PickTasksResponse plus any caplog record with level >= WARNING at tests/test_engine_ble001_1202.py:605, :609, :611, :629, :631, :633, :651, :653, :655, :673, :675, and :677. If those calls regressed from warning to error, the current tests would still pass. That does not prove the explicit AC requirement that both caught branches log at WARNING.
- AC6 PASS: no BLE001 suppression remains in serve/kanban/src/owlbear_kanban/engine.py; direct scanner test in tests/test_engine_ble001_1202.py passes
- AC7 PASS: file-scoped BLE001 lint gate for engine.py is green in both the task-owned test and the delegated ruff run
- AC8 PASS on the latest refined AC: no regressions were observed in the refined engine-related suite set; all 54 scoped tests passed

#### Security Review
- No issues found. The change stays within exception narrowing and warning logging.

#### Test Integrity
- No weakened or removed TestFromAC assertions observed in the current snapshot.

#### Test Quality
- WEAK. AC5 warning-path assertions are not exact enough to fail on an error-level regression against an explicit WARNING-level contract.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gaps
- Tighten the four AC5 warning-path tests so they assert exact logging.WARNING severity for the captured record, not >= WARNING.
- Optional hardening: seed a dispatchable task in one caught-branch warning test so post-log continuation is proved directly instead of incidentally.

#### Builder Process Quality
- CLEAN. Live implementation matches the narrowed exception contract; the remaining issue is proof strength, not source behavior.

### Deductions
- -0.12 AC5 exact WARNING-level proof gap
- Confidence: 0.88

### Verdict
- FAIL, route backlog
- Reason: the scoped implementation gate is green, but AC5 is still not proved strongly enough by the task-owned tests
- Routing note: this task body already contains two prior Review Evidence failure sections, so this rejection uses the reviewer loop-breaker route to backlog

### Required Follow-up
1. Update the four AC5 warning-path tests in tests/test_engine_ble001_1202.py to assert exact WARNING level rather than >= WARNING.
2. Re-run the task-owned suite and the refined engine-related regression gate before returning to review.

### Post-task Reflection
- Problem faced: the current snapshot is implementation-green, so the review hinged on assertion strength rather than failing runtime evidence.
- Workaround applied: used code-reader and challenger passes to separate a real AC-bound proof gap from overbroad continuation concerns.
- Pattern discovered: caplog filters written as >= target level can false-green exact-severity acceptance criteria.
- Quality gap: looped tasks can accumulate enough historical context that only the latest refined AC plus live assertions should drive the verdict.
[[2026-05-01]]


## AC5 Test Precision (Architect Re-review, 3rd cycle)

**Accept reviewer feedback.** The 4 AC5 warning-path tests in `tests/test_engine_ble001_1202.py` filter caplog records with `r.levelno >= logging.WARNING`. The AC says "log at WARNING level" — meaning exactly `WARNING`, not "at least WARNING". Change `>=` to `==` in all 4 tests:

- `test_pick_tasks_import_error_is_caught_and_logged`
- `test_pick_tasks_kanban_error_from_resolve_is_caught_and_logged`
- `test_pick_tasks_oserror_from_resolve_is_caught_and_logged`
- `test_pick_tasks_value_error_from_resolve_is_caught_and_logged`

Each test: change `r.levelno >= logging.WARNING` → `r.levelno == logging.WARNING`.

No other changes needed. Implementation is complete and correct across all 5 BLE001 sites.
[[2026-05-01]]
## Architecture Review

**Verdict:** REFINE → APPROVE — accept reviewer AC5 feedback, advance to `todo`.

### Context

Task returned to backlog after 3rd review failure (loop-breaker route). Sole remaining issue: 4 AC5 warning-path tests assert `r.levelno >= logging.WARNING` instead of exact `== logging.WARNING`. The AC says "log at WARNING level" — reviewer is technically correct that `>=` would pass if implementation regressed to `LOGGER.error()`. Previous architect rebutted; reviewer persisted across 3 cycles. Accepting the feedback to break the loop — the fix is 4 characters × 4 tests.

### AC Assessment

| AC line | Assessment | Action |
|---------|------------|--------|
| AC1-AC4 (site-specific narrowing) | PASS in 3rd review. Propagation + catch-branch tests green. | No change |
| AC5 (pick_tasks split + WARNING logs) | Implementation correct (LOGGER.warning at engine.py:2355, :2362). Tests use `>= WARNING` filter — technically allows ERROR/CRITICAL to false-green. | **Directive added:** test-writer to change `>=` → `==` in 4 tests |
| AC6 (no noqa: BLE001) | PASS | No change |
| AC7 (ruff BLE001 on engine.py) | PASS (engine-scoped) | No change |
| AC8 (task-scoped regression gate) | PASS — 54 scoped tests green | No change |

### Architecture Notes

- Implementation is complete and unchanged across all 5 BLE001 sites since builder commit `252ad283`.
- The only code change needed is in test assertions, not production code.
- Continuation proof (`isinstance(result, PickTasksResponse)`) remains valid — no early-return path exists between DR resolution and `list_tasks()` at line 2366.

### Dependency Analysis

- Depends on #1203 (archived/done). Satisfied.

### Design Diverge

Skipped — no competing approaches. Single fix: tighten 4 test assertions.

### Challenge Results

Challenger: SKIPPED — REFINE verdict (test assertion precision, no design decision).

### Test Depth

- Max depth: td:2
- Test-writer: PROCEED — change `>= logging.WARNING` → `== logging.WARNING` in 4 AC5 warning-path tests. Builder skip expected (no production code changes).
[[2026-05-01]]
## Test-Writer Notes
- Retry (4th cycle): tightened 4 AC5 warning-path test assertions from `>= logging.WARNING` to `== logging.WARNING` per architect directive and reviewer AC5 contract.
- Files: tests/test_engine_ble001_1202.py (4 caplog filters updated), no other changes.
- Commit: 0642c7ea

### Changes
- `TestFromAC_PickTasksWarningLogs::test_pick_tasks_import_error_is_caught_and_logged` — `>= WARNING` → `== WARNING`
- `TestFromAC_PickTasksWarningLogs::test_pick_tasks_kanban_error_from_resolve_is_caught_and_logged` — `>= WARNING` → `== WARNING`
- `TestFromAC_PickTasksWarningLogs::test_pick_tasks_oserror_from_resolve_is_caught_and_logged` — `>= WARNING` → `== WARNING`
- `TestFromAC_PickTasksWarningLogs::test_pick_tasks_value_error_from_resolve_is_caught_and_logged` — `>= WARNING` → `== WARNING`

### Verification
- quality-runner scoped: 54 passed, 0 failed (tests/test_engine_ble001_1202.py, tests/test_pick_tasks_resolve_1184.py, tests/test_engine_coverage.py)
- ruff: clean for both task test files

### AC coverage (unchanged)
| AC | Tests |
|----|-------|
| AC1 archive scan propagation + catch-branch | 3 tests |
| AC2 main scan propagation + catch-branch | 3 tests |
| AC3 sweep propagation + catch-branch (×4) | 6 tests |
| AC4 repair_storage propagation + catch-branch (×3) | 5 tests |
| AC5 pick_tasks propagation (×3) + warning-log (×4, now exact == WARNING) | 7 tests |
| AC6 no noqa: BLE001 | 1 test |
| AC7 ruff BLE001 engine.py | 1 test |
| AC8 td:0 | skipped |
| Total | 31 tests in 1202 + tests in 1184 |

Builder skip: test-only retry, all 31 tests green against current implementation (direct-to-review per Step 1b.1).
[[2026-05-01]]
## Builder Notes
- Implementation: no new source edits in this pass; existing `serve/kanban/src/owlbear_kanban/engine.py` narrowing remains the active implementation.
- Files changed: none.
- Tests: 54 passed, 0 failed, 0 skipped (`tests/test_engine_ble001_1202.py`, `tests/test_pick_tasks_resolve_1184.py`, `tests/test_engine_coverage.py`).
- Coverage: `owlbear_kanban.engine` 29% in scoped run (informational for this narrow maintenance task in a monolithic module).
- ruff: clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_ble001_1202.py`, and `tests/test_pick_tasks_resolve_1184.py`.
- Evidence summary: refined AC gate is green on live snapshot; no regressions detected in engine-related suites.

Post-task reflection:
- Problem faced: task history contains multiple retries and contradictory prior review notes.
- Workaround applied: treated fresh quality-runner output as the sole release authority instead of relying on historical sections.
- Pattern discovered: late-cycle builder passes are often verification-only when implementation is already complete.
- Quality gap: scoped coverage percentages on very large modules remain weak as a strict quality signal for narrow exception-handling tasks.
[[2026-05-01]]
## Review Evidence
### Scope
- Changed-file scope reconstructed from live task history and source because reviewer mode does not expose a direct `git diff` tool. Commit presence verified in `.git/logs/HEAD` for `252ad283`, `7de75b65`, and `0642c7ea`.

### Test Results
- quality-runner scoped: 54 passed, 0 failed, 0 skipped across `tests/test_engine_ble001_1202.py`, `tests/test_pick_tasks_resolve_1184.py`, and `tests/test_engine_coverage.py`

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_ble001_1202.py`, and `tests/test_pick_tasks_resolve_1184.py`

### Coverage
- `owlbear_kanban.engine`: 29%
- Informational only for this narrow maintenance task in a monolithic module

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 archive scan narrows to `CorruptionError` | `tests/test_engine_ble001_1202.py:116`, `:137`, `:382` | Yes — broad re-swallowing would break the propagation tests; losing the narrow catch would break the CorruptionError catch-branch test | COVERED |
| AC2 main scan narrows to `CorruptionError` and removes dead branch logic | `tests/test_engine_ble001_1202.py:165`, `:184`, `:412` | Yes — non-CorruptionError propagation and CorruptionError non-propagation are both pinned | COVERED |
| AC3 sweep narrows to `(FileNotFoundError, ValueError, KeyError, CorruptionError)` | `tests/test_engine_ble001_1202.py:210`, `:229`, `:441`, `:455`, `:469`, `:483` | Yes — unexpected exceptions must escape; allowed tuple returns `[]` | COVERED |
| AC4 repair_storage narrows to `(ValueError, KanbanError, OSError)` | `tests/test_engine_ble001_1202.py:267`, `:287`, `:515`, `:541`, `:561` | Yes — unexpected exceptions must propagate; allowed tuple must produce failed `RepairOutcome` entries | COVERED |
| AC5 pick_tasks splits import/call handling and logs at `WARNING` | `tests/test_engine_ble001_1202.py:319`, `:333`, `:355`, `:590`, `:615`, `:637`, `:659`; `tests/test_pick_tasks_resolve_1184.py:144`, `:164`, `:187` | Yes — unexpected import/resolve exceptions propagate, allowed resolve exceptions return successfully, and warning-path tests now filter exact `logging.WARNING` records | COVERED |
| AC6 no `# noqa: BLE001` suppressions remain | `tests/test_engine_ble001_1202.py:690` | Yes — direct token scan fails if any suppression remains | COVERED |
| AC7 Ruff BLE001 check on engine.py exits clean | `tests/test_engine_ble001_1202.py:711` | Yes — subprocess Ruff gate would fail on a real BLE001 violation in engine.py | COVERED |
| AC8 no regressions in named engine-related suites | quality-runner scoped run of `tests/test_engine_ble001_1202.py`, `tests/test_pick_tasks_resolve_1184.py`, `tests/test_engine_coverage.py` | Yes for the literal refined gate: all named suites passed in the live scoped run | COVERED |

#### Security Review
- No issues found. The implementation change stays within exception narrowing and warning logging.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current snapshot.

#### Test Quality
- STRONG. The task-owned suite now proves both propagate-path and catch-path behavior for AC1-AC5, and the AC5 warning-path tests require exact `logging.WARNING` severity.

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No blocking gaps found in the changed exception-handling paths.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `tests/test_engine_coverage.py` is useful regression context for AC8, but it is not direct branch proof for the BLE001-touched handlers. The direct proof remains in `tests/test_engine_ble001_1202.py` and `tests/test_pick_tasks_resolve_1184.py`.
- Minor docstring drift remains in the test files (`RED-phase` / old future-task wording), but it does not affect executable proof.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/engine.py:694` plus archive propagation/catch tests at `tests/test_engine_ble001_1202.py:116`, `:137`, `:382` | `test_archive_scan_non_narrowed_exception_propagates`, `test_archive_scan_attribute_error_propagates`, `test_archive_scan_corruption_error_is_caught` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:730` plus main-scan propagation/catch tests at `tests/test_engine_ble001_1202.py:165`, `:184`, `:412` | `test_main_scan_non_narrowed_exception_propagates`, `test_main_scan_oserror_propagates`, `test_main_scan_corruption_error_is_caught` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/engine.py:1585` plus sweep propagation/catch tests at `tests/test_engine_ble001_1202.py:210`, `:229`, `:441`, `:455`, `:469`, `:483` | `test_sweep_non_narrowed_exception_propagates`, `test_sweep_oserror_propagates`, `test_sweep_*_is_caught` | PASS |
| AC4 | `serve/kanban/src/owlbear_kanban/engine.py:1672` plus repair-storage propagation/catch tests at `tests/test_engine_ble001_1202.py:267`, `:287`, `:515`, `:541`, `:561` | `test_repair_storage_*_propagates`, `test_repair_storage_*_creates_failed_outcome` | PASS |
| AC5 | split handlers and warnings at `serve/kanban/src/owlbear_kanban/engine.py:2354`, `:2355`, `:2360`, `:2362`; propagate-path and warning-path tests at `tests/test_engine_ble001_1202.py:319`, `:333`, `:355`, `:590`, `:615`, `:637`, `:659`; integration ordering/propagation tests at `tests/test_pick_tasks_resolve_1184.py:144`, `:164`, `:187`; control flow continues into normal return path after the warning block at `serve/kanban/src/owlbear_kanban/engine.py:2365`, `:2381`, `:2488` | `test_pick_tasks_*_propagates`, `test_pick_tasks_*_is_caught_and_logged`, `test_resolve_pending_drs_is_called`, `test_unexpected_exception_from_resolve_propagates`, `test_resolve_runs_before_task_filtering` | PASS |
| AC6 | no `# noqa: BLE001` match found in `serve/kanban/src/owlbear_kanban/engine.py`; direct scan at `tests/test_engine_ble001_1202.py:690` | `test_engine_py_has_no_ble001_noqa` | PASS |
| AC7 | task-owned Ruff subprocess test at `tests/test_engine_ble001_1202.py:711`; quality-runner ruff exit code 0 | `test_ruff_ble001_check_passes` | PASS |
| AC8 | quality-runner scoped result: 54 passed, 0 failed, 0 skipped across the refined gate suites | delegated scoped quality run | PASS |

### Deductions
- -0.02 AC8 evidence is partly regression-context rather than direct branch proof for the touched handlers
- -0.03 changed-file scope was reconstructed from task history plus live files because no direct `git diff` tool is available in reviewer mode

### Confidence: 0.95
### Verdict: PASS
### Action: advance to docs

### Post-task Reflection
- Problem faced: the task body contained multiple historical fail/pass sections, so live evidence had to override stale narrative.
- Workaround applied: used delegated `quality-runner` and `code-reader`, then re-verified the exact source and test line references manually.
- Pattern discovered: once AC names a specific regression-suite set, that suite set governs the gate literally even if some members are broader regression context than branch-specific proof.
- Quality gap: `tests/test_engine_coverage.py` is a coarse adjacent-suite signal for this task; the task-owned suite carries the direct executable contract.
[[2026-05-01]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | BLE001 exception narrowing is an internal implementation change; no API, CLI, config, or package structure changes; no IN-scope prose doc references exception handler internals |
| 2 | Module docstrings | Yes | Updated | `pick_tasks` docstring step 2 ("Resolve") incorrectly stated "exceptions are suppressed so dispatch is never blocked" — inaccurate after narrowing to `ImportError` + `(KanbanError, OSError, ValueError)` only; updated to list suppressed types and note unexpected types propagate. `list_tasks`, `sweep`, and `repair_storage` docstrings accurate — they describe observable behavior, not exception internals |
| 3 | External attribution | No | N/A | No external patterns used; lint fix only |
| 4 | Research doc | No | N/A | No research phase |
| 5 | Diagram maintenance | Yes | Updated | `kanban.excalidraw` describes `serve/kanban/src/**` ✓ and `mcp-topology.excalidraw` describes `serve/kanban/src/**` ✓ — both footers updated from stale hashes to `Last verified: 2026-05-01 (0530874a)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings only) | Updated `pick_tasks` docstring |
| `tests/test_engine_ble001_1202.py` | OUT (test file) | N/A |
| `tests/test_pick_tasks_resolve_1184.py` | OUT (test file) | N/A |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — `pick_tasks` docstring step 2
- `share/diagrams/kanban.excalidraw` — footer hash updated
- `share/diagrams/mcp-topology.excalidraw` — footer hash updated

### Commit
`72c4e3a6` — docs: narrow pick_tasks docstring and update diagram footers (#1202, doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-01]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 archive scan narrows to CorruptionError | engine.py:694 `except CorruptionError:`; propagation + catch tests green | PASS |
| AC2 main scan narrows to CorruptionError | engine.py:730 `except CorruptionError:` + `continue`; isinstance removed | PASS |
| AC3 sweep narrows to (FNFE, VE, KE, CE) | engine.py:1585 confirmed; 6 tests cover propagation + catch | PASS |
| AC4 repair_storage narrows to (VE, KE, OSE) | engine.py:1672 confirmed; 5 tests cover propagation + failed RepairOutcome | PASS |
| AC5 pick_tasks split import/call + WARNING | engine.py:2354-2365 matches AC pattern; exact == WARNING assertions in 4 tests | PASS |
| AC6 no noqa BLE001 | grep confirms zero matches in engine.py | PASS |
| AC7 ruff BLE001 engine.py clean | quality-runner lint exit 0 | PASS |
| AC8 no engine-related regressions | 54/54 passed (task suite + test_engine_coverage.py) | PASS |

### Test Results
- pytest full suite: 3483 passed, 107 failed (all pre-existing baseline debt outside task scope), 4 skipped
- pytest task-scoped gate: 54 passed, 0 failed
- ruff: clean (0 violations)

### Architect Quality: 3/5
Initial AC listed wrong target site (_move_file), wrong exception types (yaml.YAMLError, subprocess.CalledProcessError), overly broad gates (AC7 package-wide, AC8 global-green). Required 3 architect re-reviews across 4 pipeline cycles. Final refined AC is specific and correct, but upstream quality cost significant pipeline churn.

### Deduction Breakdown
- -0.03 AC quality score 3 (notable gaps requiring multiple refinement cycles)
- -0.02 Full suite baseline has 107 unrelated failures (none task-scoped, but reduces absolute regression confidence slightly)

### Confidence: 0.95
### Action: archive

### Commits Verified
- 252ad283 fix: remove lazy duplicate-id imports in engine list_tasks (#1202, builder)
- 7a45f955 test: strengthen AC1-AC5 coverage (#1202, test-writer retry)
- 7de75b65 test: rename to match propagation assertion (#1202, test-writer)
- 0642c7ea test: tighten AC5 warning-level assertions (#1202, test-writer)
- 72c4e3a6 docs: narrow pick_tasks docstring and update diagram footers (#1202, doc-writer)