---
id: 144
title: Implement planner data models and board reader
status: archived
priority: medium
created: 2026-03-29 16:23:29.225829+02:00
updated: 2026-03-30 19:22:38.641827+02:00
started: 2026-03-30 19:21:42.245752+02:00
completed: 2026-03-30 19:21:42.245752+02:00
tags:
- phase-2
- scope:orchestrator
- type:build
depends_on:
- 14
- 153
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 17:12
## Review Evidence

### Test Results
- pytest: 27 passed, 0 failed

### Lint Results
- ruff (planner scope): All checks passed!
- Note: 14 pre-existing errors in voice/process.py (not this task)

### Coverage
- planner/__init__.py: 100%
- planner/board.py: 100%
- planner/models.py: 100%

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Task frozen + populate_by_name | models.py ConfigDict(frozen=True, populate_by_name=True); frozen tests pass | PASS |
| Task all 15 fields | models.py lines 13-27; test_roundtrip_all_15_fields asserts all 15 values | PASS |
| task_class via Field(alias=class) | models.py: task_class = Field(alias='class'); alias tests pass | PASS |
| Optional fields default None | models.py defaults; test_optional_fields_default_to_none_when_absent | PASS |
| DispatchEntry frozen 3 fields | models.py; valid + frozen + missing-field tests | PASS |
| DispatchPlan frozen entries list | models.py; plan tests: valid + frozen + empty | PASS |
| task_list_adapter TypeAdapter | models.py line 49; 4 adapter tests | PASS |
| read_board signature + 6 required args | board.py; test_default_args_include_required_flags | PASS |
| scope appends --tag | board.py lines 48-49; test_scope_filter_adds_tag_flag | PASS |
| create_subprocess_exec no shell=True | board.py lines 51-55; no shell kwarg present | PASS |
| Parse via task_list_adapter.validate_json | board.py line 62; adapter tests confirm | PASS |
| Empty board returns [] | test_empty_board_returns_empty_list | PASS |
| BoardReadError(OwlBearError) on non-zero exit | board.py raises BoardReadError(stderr_text); error tests pass | PASS |
| Stderr in error message | test_board_read_error_contains_stderr uses match= | PASS |
| FileNotFoundError propagates | No suppression; test_missing_binary_propagates_file_not_found | PASS |
| __init__.py docstring + 5 exports | __init__.py verified: docstring + __all__ with 5 symbols | PASS |
| pydantic>=2.10.0 in pyproject.toml | packages/orchestrator/pyproject.toml line 8 confirmed | PASS |

### Security: Clean (no injection, no hardcoded secrets, no path traversal)
### Test Integrity: TestFromAC classes not in builder changed files - preserved
### Test Quality: STRONG (specific assertions, error paths, async fixtures, descriptive names)

### Verdict: PASS confidence 0.97

[[2026-03-30]] Mon 17:50
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | packages/orchestrator already described as dispatch planning; planner/ is an internal impl detail |
| 2 | Docstrings | Yes | Pass | All 3 new files have module docstrings; Task, DispatchEntry, DispatchPlan, read_board, BoardReadError all documented |
| 3 | docs/sources/overview.md | Yes | Updated | Added 2 impl rows for planner/models.py (Pydantic frozen models) and planner/board.py (asyncio subprocess) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/planner-data-models-board-reader.md exists and is linked in task body |
| 6 | Scratch files | No | Pass | No docs/scratch/144-* files found |

### Files Updated
- docs/sources/overview.md (2 new rows for planner/models.py and planner/board.py)

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 19:21
## Audit
### AC Verification (spot-check, reviewer evidence accepted)
| AC Line | Evidence | Status |
|---------|----------|--------|
| Task frozen + 15 fields | models.py L11-31: ConfigDict(frozen=True, populate_by_name=True), all 15 fields present | PASS |
| task_class alias | models.py L28: Field(alias='class') | PASS |
| DispatchEntry/DispatchPlan frozen | models.py L34-49: ConfigDict(frozen=True) on both | PASS |
| task_list_adapter | models.py L52: TypeAdapter(list[Task]) | PASS |
| read_board signature + subprocess_exec | board.py L20-64: async, typed params, create_subprocess_exec, no shell=True | PASS |
| BoardReadError(OwlBearError) | board.py L15-16: inherits OwlBearError, raised with stderr | PASS |
| __init__.py docstring + exports | __init__.py: docstring, __all__ with 6 public symbols | PASS |
| pydantic>=2.10.0 in pyproject.toml | packages/orchestrator/pyproject.toml L8 | PASS |

### Test Results
- pytest (task scope): 27 passed, 0 failed (0.20s)
- pytest (full suite): 1535 passed, 140 failed (pre-existing, none in planner scope)
- ruff: All checks passed

### Architect Quality
- AC specificity: Excellent. Architect rewrote vague originals into precise specs.
- Edge case coverage: Complete (empty board, missing binary, non-zero exit).
- AC quality score: 5/5

### Deduction breakdown: (none)
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 19:22
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 40577f4 | chore | kanban/tasks/144-*.md | #144 |
