---
id: 722
title: 'P3-10: GREEN — task CRUD operations'
status: todo
priority: critical
created: 2026-04-09T03:26:03.5311612+02:00
updated: 2026-04-09T17:28:43.4808676+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 720
    - 721
class: standard
---

## Objective
Implement create_task, edit_task, move_task on KanbanEngine.

Brief: see parent #712

## AC
- [ ] `create_task(title, ...)` allocates next_id from config, writes task file, increments config next_id
- [ ] `edit_task(task_id, ...)` modifies task fields, writes back, updates `updated` timestamp
- [ ] `edit_task` append_body with optional `[[YYYY-MM-DD]]` timestamp prefix
- [ ] `move_task(task_id, status)` changes status, handles archive
- [ ] Slug frozen at creation — edit title does not rename file
- [ ] All #721 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — add CRUD methods)

[[2026-04-09]] Thu 17:28
## Architecture Review

### Context
GREEN phase task — implement `create_task`, `edit_task`, `move_task` on `KanbanEngine` in `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`. Parent #712 (archived epic). Dependency #721 (done — 36 RED tests). **Added missing dependency on #720** (creates engine.py with KanbanEngine class, `list_tasks()`, `show_task()`). Building blocks: `task_io.py` (#718, done), `config_loader.py` (#716, done), `engine_models.py` (#714, done).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `create_task(title, ...)` allocates next_id, writes file, increments config | PASS — clear: `load_config` → allocate `next_id` → `make_task_filename` + `write_task` → `save_config` with incremented next_id. 4 tests verify exact values. | None |
| `edit_task(task_id, ...)` modifies fields, writes back, updates `updated` | PASS — 12 tests define exact parameter set (title, body, priority, status, parent, add_tags, remove_tags, add_deps, remove_deps, blocked, block_reason). Note: no test verifies `updated` timestamp change, but AC line is binding independently — builder must implement. | Builder: add builder-discovered test for `updated` field change |
| `edit_task` append_body with `[[YYYY-MM-DD]]` timestamp prefix | PASS — 3 tests verify format, ordering, and content preservation. Regex `\[\[\d{4}-\d{2}-\d{2}\]\]` is precise. | None |
| `move_task(task_id, status)` changes status, handles archive | PASS — 6 valid-status tests, 2 archive tests, 3 invalid-status tests. Archive behavior per brief: "move task file to archived location or mark status." | None |
| Slug frozen at creation — edit title does not rename file | PASS — architecturally clear. Note: no test coverage (tests only verify record.title changes). Builder must locate file by `{id}-*.md` glob, not regenerate from title. | Builder: add builder-discovered test for filename stability after title edit |
| All #721 tests pass | PASS — clear exit gate. 36 tests across 3 TestFromAC classes. | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 CRUD methods on existing KanbanEngine class |
| Interface clarity | PASS | Test file defines exact parameter signatures; AC lines are specific |
| Dependency correctness | PASS (after fix) | Added #720 — engine.py created there. Tests use `show_task()` and `list_tasks()` from #720. |
| Module layering | PASS | Engine module inside mcp-kanban, uses task_io + config_loader from same package |
| TDD compliance | PASS | RED #721 done with 36 tests |
| KISS/YAGNI | PASS | Only 3 methods, no extras |
| Premise challenge | PASS | CRUD is fundamental engine functionality |
| Pattern consistency | PASS | Follows task_io.write_task, config_loader.save_config, engine_models.TaskRecord patterns |
| Security surface | PASS | Path containment via task_io.validate_path_containment; slug sanitization via generate_slug; both already implemented in #718 |
| Single domain | PASS | Kanban engine domain exclusively |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| create_task | config.yml missing/corrupt | FileNotFoundError from load_config | Yes (propagates) | Clear error |
| create_task | disk full on write_task | IOError | Yes (propagates from task_io) | Clear error |
| edit_task | task_id not found | FileNotFoundError (no matching `{id}-*.md`) | Builder must handle | Should raise with clear message |
| move_task | invalid status | ValueError/KeyError | Yes (3 tests verify) | Clear error |
| move_task | task_id not found | Same as edit_task | Builder must handle | Should raise with clear message |

### Architecture Notes
1. **Dependency fix:** Added #720 to depends_on. Engine.py is created by #720 with KanbanEngine class + `list_tasks()` + `show_task()`. Tests `test_move_task_archived_not_in_active_tasks` calls `engine.list_tasks()` and `test_edit_no_changes_returns_unchanged_record` calls `engine.show_task()` — both from #720.
2. **File lookup pattern:** For edit_task and move_task, builder must find task files by `{id}-*.md` glob in tasks_dir (slug frozen, don't regenerate from title). Existing `validate_path_containment` from task_io.py should be used on resolved paths.
3. **Timestamp generation:** Use ISO 8601 strings matching existing Go nanosecond format in codebase (e.g., `2026-04-09T03:26:03.5311612+02:00`). `datetime.now(tz=timezone.utc).isoformat()` is acceptable — precision difference is fine per engine_models.py comment.
4. **Builder-discovered tests recommended:** (a) Verify `updated` field changes on edit_task; (b) Verify filename unchanged after title edit. Both are AC requirements without RED test coverage.
5. **Archive implementation:** Brief says "Move task file to archived location or mark status." Check if `v1-archive/` directory pattern is used for archived tasks (listing tests reference it). If tasks_dir has a sibling archive dir, move file there; otherwise set status. Test is intentionally permissive.

### Challenge Results
- Challenger: reconsider (test gaps for AC2 updated timestamp, AC5 slug frozen, archive behavior, concurrency)
- Architect response: Rebutted. AC lines are binding independent of test coverage — builder must implement. Concurrency rejected per D2 (YAGNI). Archive behavior specified in brief. Test gaps addressed via builder-discovered tests recommendation. Dependency fix (#720 added) resolves import/method availability.

### Verdict: APPROVE
### Action Taken: Added #720 to depends_on (was missing — engine.py created by #720). Approved to todo. Builder guidance: add builder-discovered tests for `updated` timestamp change and filename stability after title edit.
