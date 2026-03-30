# Planner Data Models & Board Reader — Research Validation

> **Owning task:** #144 — Implement planner data models and board reader
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #144 (subtask of #20) asks for Pydantic models (`Task`, `DispatchEntry`,
`DispatchPlan`) and an async board reader wrapping `kanban-md.exe list --json`.
Parent research: `docs/research/build-dispatch-planner.md` S3.3, S3.5.

Key validation questions: (1) Is the AC still accurate against current codebase?
(2) Does the orchestrator package support a `planner/` subpackage? (3) What's the
exact kanban-md JSON schema? (4) Are there missing dependencies or AC gaps?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | `mcp-kanban/server.py` (codebase) | .95 | `_run_kanban()` subprocess pattern, `AppContext` binary discovery |
| S2 | `voice/protocol.py` (codebase) | .90 | Pydantic frozen model convention: `ConfigDict(frozen=True)` |
| S3 | Pydantic v2 docs — Models | .90 | `model_validate_json()`, `TypeAdapter`, `ConfigDict` |
| S4 | Python 3.12 asyncio-subprocess docs | .85 | `create_subprocess_exec` with PIPE, `communicate()` |
| S5 | `build-dispatch-planner.md` (parent research) | .95 | S3.3 board reading strategy, S3.5 implementation approach |
| S6 | `dispatch-planning` SKILL.md | .90 | Agent dispatch mapping, gate algorithm, JSON output format |
| S7 | `orchestrator/pyproject.toml` (codebase) | .85 | Package build targets, dependency list |
| S8 | `owlbear/errors.py` (codebase) | .80 | `OwlBearError` base exception pattern |
| S9 | kanban-md actual `--json` output | .95 | Validated schema from live board |

## 3. Analysis

### 3.1 kanban-md JSON Schema (validated from live output)

| Field | Type | Always present | Notes |
|-------|------|:-:|-------|
| `id` | int | Yes | Task identifier |
| `title` | str | Yes | |
| `status` | str | Yes | One of 7 pipeline statuses |
| `priority` | str | Yes | One of 5 priority levels |
| `created` | str (ISO 8601) | Yes | |
| `updated` | str (ISO 8601) | Yes | |
| `started` | str (ISO 8601) | No | Set on done/archived |
| `completed` | str (ISO 8601) | No | Set on done/archived |
| `tags` | list[str] | Yes | May be empty |
| `depends_on` | list[int] | Yes | May be empty |
| `claimed_by` | str | No | Present when claimed |
| `claimed_at` | str (ISO 8601) | No | Present when claimed |
| `class` | str | Yes | e.g. "standard" |
| `body` | str | Yes | Full markdown body |
| `file` | str | Yes | Absolute path |

The `--json` flag returns a JSON array of these objects. [S9]

### 3.2 Pydantic Model Design

| Approach | Pattern | Source |
|----------|---------|--------|
| Frozen models | `ConfigDict(frozen=True)` | voice/protocol.py [S2] |
| JSON parsing | `TypeAdapter[list[Task]].validate_json(stdout)` | Pydantic docs [S3] |
| Optional fields | `datetime | None = None` | Standard Pydantic [S3] |
| Field alias | `model_config = ConfigDict(populate_by_name=True)` if needed | Not needed — JSON keys match Python names |

The `class` field in kanban-md conflicts with Python's `class` keyword. Use
Pydantic's `Field(alias="class")` with `populate_by_name=True`, or name the
field `task_class` with a serialization alias. [S3, S9]

### 3.3 Board Reader Pattern Comparison

| Aspect | mcp-kanban `_run_kanban()` | Proposed `read_board()` |
|--------|---------------------------|------------------------|
| API | `async def _run_kanban(ctx, *args)` | `async def read_board(kanban_bin, kanban_dir, **filters)` |
| Subprocess | `create_subprocess_exec` (no shell) | Same — injection-safe [S4] |
| Args | `--no-color --dir {kanban_dir}` | `list --json --unblocked --not-blocked --unclaimed --no-color --dir {dir}` |
| Return | `(stdout, stderr, rc)` tuple | `list[Task]` (parsed) |
| Error: missing binary | `FileNotFoundError` in lifespan | `FileNotFoundError` at call site |
| Error: non-zero rc | Caller checks rc | `BoardReadError(OwlBearError)` |
| Error: empty board | N/A | Return empty `list[Task]` |

### 3.4 Dependency and Packaging Gap

The orchestrator `pyproject.toml` [S7] lists only `agent-client-protocol>=0.9.0`.
Pydantic 2.12.5 is available transitively but **not declared explicitly**.
The `knowledge` package declares `pydantic>=2.10.0` — the orchestrator should do
the same for correctness. [S7]

Build targets include `src/owlbear` — a new `src/owlbear/planner/` subpackage
will be picked up automatically with an `__init__.py`. No pyproject.toml changes
needed beyond the dependency addition. [S7]

## 4. Recommendation (.90 confidence)

AC is valid and ready for architect review. Two refinements suggested:

1. **Add explicit `pydantic>=2.10.0` dependency** to `packages/orchestrator/pyproject.toml`.
   Currently transitive only — fragile if ACP SDK drops pydantic. (.90)

2. **Handle `class` field name conflict** via `Field(alias="class")` with
   `ConfigDict(populate_by_name=True)`. This is a minor implementation detail
   the architect should note in the refined AC. (.85)

Risks:
- kanban-md JSON schema coupling — mitigated by testing against canned output
- Large `body` field in Task model — needed for gate checks (TW:MISSING, AC:MISSING)
  but downstream modules should not assume body is small

## 5. Follow-up Tasks

No new tasks needed — #144 is already scoped correctly. The architect will refine
the AC during backlog review. Sibling tasks #145 and #146 cover the remaining
planner and orchestrator scope.
