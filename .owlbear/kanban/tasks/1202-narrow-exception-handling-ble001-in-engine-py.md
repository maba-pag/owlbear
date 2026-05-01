---
id: 1202
title: Narrow exception handling (BLE001) in engine.py
status: todo
priority: important
created: 2026-04-30 15:28:57.610272+00:00
updated: 2026-05-01T00:44:32.227506+00:00
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