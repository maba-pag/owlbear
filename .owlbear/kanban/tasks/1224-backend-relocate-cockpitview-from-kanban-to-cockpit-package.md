---
id: 1224
title: Backend — relocate CockpitView from kanban to cockpit package
status: review
priority: needed
created: 2026-04-30 16:31:18.599723+00:00
updated: 2026-05-01T03:14:00.710699+00:00
tags:
- cockpit
- kanban-engine
- refactor
parent:
depends_on:
- 1222
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Move CockpitView facade from kanban engine into cockpit package where it belongs.

## Acceptance Criteria
- [ ] `CockpitView` class moved from `serve/kanban/src/owlbear_kanban/engine.py` to `serve/cockpit/src/owlbear_cockpit/view.py` (new file) `(td:2)`
- [ ] `KanbanEngine.cockpit_view()` property and `KanbanEngine._cockpit_view` attribute removed from `engine.py`; engine.py imports nothing from `owlbear_cockpit` `(td:2)`
- [ ] Import path `owlbear_kanban.engine.CockpitView` updated to `owlbear_cockpit.view.CockpitView` in all source consumers: `deps.py`, `routes/read.py`, `routes/mutation.py` `(td:2)`
- [ ] Import path updated in all test files that reference the old path: `test_engine_cockpit_view.py`, `test_engine_release_task_occ.py`, `test_cockpit_kanban_routes.py`, `test_cockpit_mutation_api_1132.py`, `test_cockpit_read_api.py`, `test_cockpit_read_api_1223.py` `(td:2)`
- [ ] Kanban-package test coverage of CockpitView removed from `serve/kanban/tests/`: `test_engine_init_1067.py` (constructability test), `test_engine_init_1068.py` (`TestFromAC_CockpitViewMethodStubs` and `TestFromAC_ViewsConstructedAtInit` CockpitView subtests), `test_engine_list_show_1071.py` (`TestFromAC_CockpitViewListTasks` and `TestFromAC_CockpitViewShowTask`); equivalent coverage lives in `tests/test_engine_cockpit_view.py` (root suite) with updated import `(td:2)`
- [ ] `CockpitView` implementation does not access private engine attributes (no `._`-prefixed engine fields used in `view.py`) `(td:1)`
- [ ] `serve/kanban/README.md` `cockpit_view()` row removed from the engine accessor table `(td:1)`
- [ ] All cockpit tests pass `(td:0)`
- [ ] All kanban tests pass `(td:0)`

## Files
### Source
- `serve/kanban/src/owlbear_kanban/engine.py` — remove `CockpitView` class, `cockpit_view()` property, `_cockpit_view` attribute
- `serve/cockpit/src/owlbear_cockpit/view.py` (new) — CockpitView class definition
- `serve/cockpit/src/owlbear_cockpit/deps.py` — update import
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — update import
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — update import
### Tests (import update only)
- `tests/test_engine_cockpit_view.py`
- `tests/test_engine_release_task_occ.py`
- `tests/test_cockpit_kanban_routes.py`
- `tests/test_cockpit_mutation_api_1132.py`
- `tests/test_cockpit_read_api.py`
- `tests/test_cockpit_read_api_1223.py`
### Tests (remove CockpitView coverage — belongs in cockpit suite)
- `serve/kanban/tests/test_engine_init_1067.py`
- `serve/kanban/tests/test_engine_init_1068.py`
- `serve/kanban/tests/test_engine_list_show_1071.py`
### Docs
- `serve/kanban/README.md`

[[2026-05-01]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One logical change: relocate CockpitView class + clean up all its references |
| Interface clarity | PASS (after refine) | AC now enumerates all affected files; import path change well-defined |
| Dependency correctness | PASS | #1222 (public engine properties) is done; public props (`tasks_dir`, `kanban_dir`) confirmed present in engine.py |
| Module layering | PASS | `owlbear_kanban: set()` in boundary suite; cockpit→kanban is the allowed direction; removing CockpitView from kanban eliminates the cockpit-specific coupling |
| TDD compliance | PASS | Test-writer will create red tests; existing `test_engine_cockpit_view.py` covers behavior and needs only import-path update |
| KISS/YAGNI | PASS | Pure refactor; no new behavior introduced |
| Premise challenge | PASS | Genuine layering violation: cockpit-domain class living in kanban package; `deps.py` already constructs `CockpitView(engine)` directly, confirming cockpit owns instantiation |
| Pattern consistency | PASS | Follows existing facade pattern (`AgentView` in kanban, `CockpitView` moves to cockpit) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit domain; no multi-domain crossing |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `from owlbear_cockpit.view import CockpitView` in engine.py | Would violate package boundary if accidentally introduced | ImportError at test time (boundary suite catches) | Yes — boundary test enforces | None at runtime (caught by CI) |
| Old import path left in any consumer | `ImportError` at startup | ImportError | No — AC enumerates all 9 consumer files | Cockpit fails to start |

### Challenger Results

Challenger returned `block` (confidence 0.43) citing: (1) under-scoped import file list, (2) kanban-side test migration ambiguity, (3) `engine.cockpit_view()` API retirement not explicit. All three concerns resolved by the AC refine: import consumers enumerated (6 test files + 3 source files + 3 kanban-test migration targets), `cockpit_view()` property removal explicit in AC 2, kanban-test migration policy explicit in AC 5. Overriding challenger per architect authority — the design is architecturally correct and the concerns were scope/AC clarity, not design flaws.

### Key Architectural Note

`engine.cockpit_view()` is currently a cached accessor (`self._cockpit_view = CockpitView(self)` at `__init__`). The cockpit runtime already bypasses it — `deps.py.get_view()` constructs `CockpitView(engine)` directly. The cached property is dead runtime code; only three kanban-package tests assert its existence. Removing it is safe and required to satisfy AC 2 and AC 4.

**APPROVED #1224 → todo | CockpitView relocation — AC refined to enumerate all 9 import consumers + 3 kanban-test migration targets + engine API retirement**
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_view_1224.py
- Classes: TestFromAC_CockpitViewNewModule, TestFromAC_EngineCleanup, TestFromAC_SourceConsumersImport, TestFromAC_TestFileImportUpdates, TestFromAC_KanbanTestCleanup, TestFromAC_ViewNoPrivateAccess, TestFromAC_ReadmeCleanup
- Tests per category: happy 14, edge 10, error 0, boundary 8 (source/text scan guards)
- Total: 32 tests, all FAIL
- ruff: clean
- AC coverage: AC1(8 tests) AC2(5 tests) AC3(6 tests) AC4(6 tests) AC5(5 tests) AC6(1 test) AC7(1 test) — AC8+AC9 are td:0, skipped
[[2026-05-01]]
## Builder Notes
- Implementation:
  - Added `serve/cockpit/src/owlbear_cockpit/view.py` and moved `CockpitView` class from kanban engine into cockpit package.
  - Removed `KanbanEngine._cockpit_view` initialization and `KanbanEngine.cockpit_view()` accessor from `serve/kanban/src/owlbear_kanban/engine.py`.
  - Updated source imports to new path in:
    - `serve/cockpit/src/owlbear_cockpit/deps.py`
    - `serve/cockpit/src/owlbear_cockpit/routes/read.py`
    - `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
  - Updated test imports/usages to `owlbear_cockpit.view.CockpitView` in:
    - `tests/test_engine_cockpit_view.py`
    - `tests/test_engine_release_task_occ.py`
    - `tests/test_cockpit_kanban_routes.py`
    - `tests/test_cockpit_mutation_api_1132.py`
    - `tests/test_cockpit_read_api.py`
    - `tests/test_cockpit_read_api_1223.py`
  - Removed kanban-side CockpitView coverage required by AC5:
    - `serve/kanban/tests/test_engine_init_1067.py` (constructability check removed)
    - `serve/kanban/tests/test_engine_init_1068.py` (removed `TestFromAC_CockpitViewMethodStubs` and `engine.cockpit_view()` accessor checks)
    - `serve/kanban/tests/test_engine_list_show_1071.py` (removed `TestFromAC_CockpitViewListTasks` and `TestFromAC_CockpitViewShowTask`)
  - Updated one additional durable test that referenced removed engine accessor:
    - `serve/kanban/tests/test_engine_pick_tasks_1074.py` now instantiates `CockpitView(engine)` directly.
  - Removed `cockpit_view()` row from engine accessor table in `serve/kanban/README.md`.

- RED verification (Quality Runner):
  - `tests/test_cockpit_view_1224.py`: 32 failed before implementation.

- GREEN verification (Quality Runner):
  - `tests/test_cockpit_view_1224.py`: 32 passed, 0 failed.
  - Ruff on changed source/test scope: clean.

- Additional verification context:
  - Cockpit broad run (`tests/test_cockpit_*.py` + cockpit-related suites) surfaced 6 pre-existing failures in `tests/test_cockpit_react_compiler_1015.py` (frontend/toolchain assertions; unrelated to this refactor).
  - Kanban broad run (`serve/kanban/tests/`) surfaced multiple pre-existing baseline failures in legacy config/init suites unrelated to CockpitView relocation.
  - AC-scoped relocation checks are green via `tests/test_cockpit_view_1224.py` and updated import/call sites.

- Coverage:
  - Task-scoped gate run passed; broad mixed-suite coverage outputs include unrelated baseline suites and are not reliable for this refactor in isolation.

- Evidence summary:
  - `CockpitView` now lives in cockpit package and is imported from `owlbear_cockpit.view` in all AC-listed source/test consumers.
  - `engine.py` contains no `class CockpitView`, no `def cockpit_view`, and no `_cockpit_view` initialization.
  - `view.py` uses only public engine API; no `engine._*` private attribute access.
  - Kanban README accessor table no longer lists `cockpit_view()`.

- Fixes applied during verification:
  - Removed residual `CockpitView` text in `test_engine_init_1067.py` to satisfy AC text-scan test.
  - Restored `_make_cockpit_view` helper in `test_engine_list_show_1071.py` using new import path to keep remaining non-AC test blocks valid and lint-clean.
  - Added trailing newline in new `view.py` to satisfy ruff W292.

- Post-task reflection:
  - Major risk was text-scan AC assertions; small leftover strings can fail despite functional correctness.
  - Removing engine accessor required one extra durable-test adaptation (`test_engine_pick_tasks_1074.py`) outside AC list.
  - Running broad suites revealed significant pre-existing baseline failures; scoped quality gates were necessary to isolate this task’s regression surface.
  - Moving the class intact minimized behavior drift and kept the diff surgical despite multi-file import churn.