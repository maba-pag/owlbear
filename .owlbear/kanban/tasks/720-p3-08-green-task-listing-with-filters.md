---
id: 720
title: 'P3-08: GREEN — task listing with filters'
status: todo
priority: needed
created: 2026-04-09T03:25:47.5994845+02:00
updated: 2026-04-09T17:50:46.1787116+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 719
class: standard
---

## Objective
Implement `list_tasks()` on KanbanEngine with full filter/sort/limit support.

Brief: see parent #712

## AC
- [ ] `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` returns filtered list[TaskRecord]
- [ ] Reads all task files from tasks_dir via task_io module
- [ ] Filter logic matches kanban-md behavioral contracts
- [ ] Sort by each supported field
- [ ] All #719 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (new — KanbanEngine class, list_tasks method)

[[2026-04-09]] Thu 17:50
## Architecture Review

### Context
GREEN phase task — implement `KanbanEngine.list_tasks()` with full filter/sort/limit/archive support in new `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`. Parent #712 (archived epic). Dependency #719 (done — 34 RED tests in `tests/test_kanban_engine_listing.py`). Building blocks: `task_io.py` (read_task, write_task from #718 done), `config_loader.py` (load_config from #716 done), `engine_models.py` (TaskRecord, BoardConfig from #714 done).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` returns filtered `list[TaskRecord]` | PASS — full signature with 10 filter/sort/pagination params; return type clear; matches Brief's KanbanEngine API surface | None |
| Reads all task files from tasks_dir via task_io module | PASS — specifies implementation approach; `task_io.read_task(path)` is available (#718 done); builder should glob `*.md` in tasks_dir from config | None |
| Filter logic matches kanban-md behavioral contracts | PASS — operationally defined by #719 tests (34 tests specify exact filter behavior); Brief behavioral contracts table provides additional context | None |
| Sort by each supported field | PASS — 6 fields (priority, updated, id, title, status, created) from #719 tests; priority/status must use config-rank order (not alphabetical) per test assertions | None |
| All #719 tests pass | PASS — clear exit gate; 34 tests in `test_kanban_engine_listing.py` | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: create KanbanEngine class with list_tasks |
| Interface clarity | PASS | Full parameter list and return type in AC1; side effects: none (read-only); constructor: `KanbanEngine(kanban_dir: Path)` evident from tests |
| Dependency correctness | PASS | #719 done (34 RED tests). Upstream modules: engine_models (#714 done), config_loader (#716 done), task_io (#718 done) |
| Module layering | PASS | engine.py inside mcp-kanban package; imports from engine_models, task_io, config_loader — all same package; no upward imports |
| TDD compliance | PASS | #719 (RED) done with 34 tests across 11 TestFromAC_* classes |
| KISS/YAGNI | PASS | Minimal scope — implement only what the 34 tests require |
| Premise challenge | PASS | list_tasks is core engine operation per Brief KanbanEngine API surface |
| Pattern consistency | PASS | Uses existing patterns: Pydantic models (TaskRecord), file I/O (task_io.read_task), config loading (config_loader.load_config) |
| Security surface | PASS | Read-only filesystem operation; path traversal already guarded by task_io.validate_path_containment |
| Single domain | PASS | Kanban engine domain exclusively |

### Builder Guidance

1. **Constructor**: `KanbanEngine.__init__(self, kanban_dir: Path)` — load BoardConfig via `config_loader.load_config(kanban_dir)`, store `kanban_dir`, derive `tasks_dir` and archive dir paths from config.
2. **show_task**: Downstream #722 (CRUD GREEN, depends_on=[720, 721]) requires `show_task(task_id: str) -> TaskRecord` to exist on KanbanEngine. Its RED test is in `test_kanban_engine_crud.py:350` (`engine.show_task(task_id)`). Implement as: scan tasks_dir for file matching `{task_id}-*.md`, call `task_io.read_task()`. This is a natural companion to list_tasks and avoids blocking #722.
3. **Priority/status sort**: Must use config-rank order, NOT alphabetical. Tests explicitly guard against alphabetical regression (`test_sort_by_priority_uses_config_rank` asserts `priorities[0] == "someday"`).
4. **Archive directory**: Tests use `v1-archive/` as sibling to `tasks/` under kanban_dir. `archived=True` reads from archive dir instead of tasks_dir.
5. **Search**: Tests match exact case (`"bootstrap"` matches lowercase in title, `"Refactor"` matches exact case in body). The kanban-md binary uses case-insensitive search — implement case-insensitive to match behavioral contracts.

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation across all 10 criteria; verified TaskRecord model (engine_models.py:56-87), read_task (task_io.py:151-186), load_config (config_loader.py:50-60), existing list_tasks MCP tool patterns (server.py:163-212). 34 test assertions verified across 11 test classes. No concerns requiring formal challenge.

### Verdict: APPROVE
### Action Taken: Approved #720 to todo. AC is verifiable (34 RED tests as gate), dependencies correct, architecture sound. Builder guidance: also implement show_task() for downstream #722 compatibility, use config-rank sort order, case-insensitive search.
