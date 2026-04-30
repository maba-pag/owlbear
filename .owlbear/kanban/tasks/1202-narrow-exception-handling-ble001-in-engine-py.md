---
id: 1202
title: Narrow exception handling (BLE001) in engine.py
status: backlog
priority: important
created: 2026-04-30 15:28:57.610272+00:00
updated: 2026-04-30T22:46:54.102440+00:00
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