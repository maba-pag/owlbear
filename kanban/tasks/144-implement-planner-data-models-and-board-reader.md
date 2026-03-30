---
id: 144
title: Implement planner data models and board reader
status: review
priority: needed
created: 2026-03-29T16:23:29.2258287+02:00
updated: 2026-03-30T07:53:10.0131269+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 14
    - 153
class: standard
---

See docs/research/planner-data-models-board-reader.md for validated research.
See docs/research/build-dispatch-planner.md S3.3, S3.5 for parent design.

## Acceptance Criteria

### models.py â€” packages/orchestrator/src/owlbear/planner/models.py

- [ ] `Task` model â€” frozen Pydantic BaseModel (`ConfigDict(frozen=True, populate_by_name=True)`) with fields:
  - `id: int`, `title: str`, `status: str`, `priority: str`
  - `created: datetime`, `updated: datetime`
  - `started: datetime | None = None`, `completed: datetime | None = None`
  - `tags: list[str]`, `depends_on: list[int]`
  - `claimed_by: str | None = None`, `claimed_at: datetime | None = None`
  - `task_class: str` via `Field(alias=class)` (Python keyword conflict)
  - `body: str`, `file: str`
- [ ] `DispatchEntry` model â€” frozen: `task_id: int`, `agent: str`, `target_status: str`
- [ ] `DispatchPlan` model â€” frozen: `entries: list[DispatchEntry]`
- [ ] `task_list_adapter = TypeAdapter(list[Task])` module-level constant for JSON parsing

### board.py â€” packages/orchestrator/src/owlbear/planner/board.py

- [ ] `async def read_board(kanban_bin: Path, kanban_dir: Path, *, scope: str | None = None) -> list[Task]`
  - Calls kanban-md.exe with args: `list --json --unblocked --not-blocked --unclaimed --no-color --dir {kanban_dir}`
  - When `scope` is provided, appends `--tag {scope}` to args
  - Uses `asyncio.create_subprocess_exec` (never `shell=True`) for injection safety
  - Parses stdout via `task_list_adapter.validate_json(stdout)`
  - Returns `list[Task]` (empty list when board has no matching tasks)
- [ ] `class BoardReadError(OwlBearError)` â€” raised on non-zero exit code, includes stderr in message
  - `FileNotFoundError` from subprocess propagates naturally on missing binary

### Infrastructure

- [ ] `packages/orchestrator/src/owlbear/planner/__init__.py` â€” module docstring, public imports (Task, DispatchEntry, DispatchPlan, read_board, BoardReadError)
- [ ] Add `pydantic>=2.10.0` to `packages/orchestrator/pyproject.toml` dependencies

### Patterns to follow

- Frozen models: voice/protocol.py `ConfigDict(frozen=True)` convention
- Subprocess: mcp-kanban server.py `_run_kanban()` pattern (create_subprocess_exec, PIPE, no shell)
- Errors: OwlBearError base from owlbear.errors

[[2026-03-29]] Sun 19:28
## Architecture Review
**Verdict:** APPROVED (AC refined, TDD test task created)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Pydantic models (Task, DispatchEntry, DispatchPlan) in models.py | Vague: no field specs, no config details | Rewritten: all 15 Task fields, alias handling, frozen config, DispatchEntry/DispatchPlan fields |
| Board reader in board.py calls kanban-md | Vague: no function signature, no error types | Rewritten: exact signature, args, parse strategy, BoardReadError |
| Handles empty board, missing binary, non-zero exit | Missing: no error class name, no exception propagation spec | Rewritten: BoardReadError(OwlBearError), FileNotFoundError propagation |
| Unit tests with mocked subprocess | Bundled into impl task, violates TDD | Removed from impl AC, created test task #153 |
| (missing) class field keyword conflict | Not in original AC, identified by research | Added: Field(alias=class) with populate_by_name |
| (missing) pydantic dependency | Not in original AC, transitive only | Added: pydantic>=2.10.0 in pyproject.toml |
| (missing) __init__.py | Not in original AC | Added: planner package init with public imports |

### Architecture Notes
- Single domain: scope:orchestrator (planner/ subpackage only)
- Follows voice/protocol.py frozen model convention (ConfigDict(frozen=True))
- Follows mcp-kanban server.py _run_kanban() subprocess pattern (create_subprocess_exec, PIPE, no shell)
- BoardReadError subclasses OwlBearError from owlbear.errors
- Greenfield: planner/ directory does not exist yet, no conflicts
- No module layering concerns: models.py is a leaf (no cross-package imports beyond pydantic); board.py imports from models.py + owlbear.errors only
- asyncio.create_subprocess_exec (never shell=True) prevents command injection
- No new user-input boundary: read_board takes typed Python params, not user strings

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| read_board() | Binary not found | FileNotFoundError | Yes, propagates | Planner cannot read board |
| read_board() | Non-zero exit code | BoardReadError | Yes, raised with stderr | Dispatch cycle skipped |
| read_board() | Empty board | N/A | Yes, returns [] | No tasks dispatched (nominal) |
| read_board() | Invalid JSON stdout | ValidationError | No (bug in kanban-md) | Unhandled crash, follow-up if seen |
| Task model | class field absent in JSON | ValidationError | No (schema violation) | Parse failure, surfaced naturally |

### Changes Made
- Rewrote task body with precise AC (15 Task fields, function signatures, error types, infrastructure items)
- Created test task #153 (Test: planner data models and board reader) at todo
- Added depends_on #153 to #144
- Removed bundled unit test AC from impl task (moved to #153)

### Dependencies
- Verified: #14 (Build mcp-kanban server) archived
- Added: #153 (TDD RED tests) at todo, #144 depends on it
- Verified: #145 and #146 depend on #144, still in ideation (unaffected)

[[2026-03-30]] Mon 07:53
## Builder Notes
- Files changed: packages/orchestrator/pyproject.toml, packages/orchestrator/src/owlbear/planner/__init__.py (new), packages/orchestrator/src/owlbear/planner/models.py (new), packages/orchestrator/src/owlbear/planner/board.py (new)
- Tests: 27 passed, coverage 100% on planner/__init__.py, planner/models.py, planner/board.py
- Lint: ruff clean
- Evidence: 27 passed in 0.26s, ruff all checks passed
- Fixes applied: datetime import noqa TC003 (needed at runtime for Pydantic schema resolution); Path moved to TYPE_CHECKING in board.py
