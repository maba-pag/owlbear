# Data Person — Position on Kanban Engine Data Model

## Data Quality Stance

**One canonical `Task` model in the engine package, with schema-validated projections — no hand-built dicts, no ad-hoc key stripping.**

The restructured engine should export exactly two Pydantic models:

1. **`Task`** (renamed from `TaskRecord`) — the canonical domain model. `extra='allow'` preserved for round-trip fidelity of unknown/vendor YAML frontmatter keys. Owns all fields: id, title, status, priority, created, updated, body, tags, parent, depends_on, blocked, block_reason, claimed_by, claimed_at.

2. **`TaskSummary`** — a schema-validated projection for list views (replaces the hand-built dict in `list_tasks`). Fields: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on. No body, no timestamps, no file path. This is a domain concept ("task identity and state at a glance"), not a UI concern — all consumers need it.

The MCP boundary model (`KanbanTask`) stays in the MCP server package as a thin adapter. It converts `claimed_by` → `claimed` bool, sets `extra='ignore'` to enforce wire-protocol discipline, and may optionally populate a `file` field at the adapter layer. The canonical engine model has no file path — that's an implementation detail.

No file path on the canonical model. The `file` field on `KanbanTask` today is always `None` — a field that exists but is never populated is worse than no field at all. If agents need file paths for discoverability, the MCP adapter populates it; the engine stays clean.

## Schema and Validation Reasoning

### Timestamps: Keep as strings

Timestamps stay as `str` in both the canonical model and on disk. This is not just legacy Go compatibility — it's **round-trip fidelity**. Existing task files carry Go 7-digit nanosecond timestamps (`2026-04-09T03:24:26.6974428+02:00`); new ones carry Python microsecond timestamps (`2026-04-09T03:24:26.697442+00:00`). String storage preserves both verbatim without lossy truncation.

The `_NoTimestampLoader` in `task_io.py` stays — it prevents the YAML parser from coercing timestamp strings to `datetime` objects, which would truncate nanoseconds on parse.

**Critical caveat for sorting:** The engine currently sorts by `created`/`updated` using raw string comparison (`tasks.sort(key=lambda t: t.created)`). This produces **wrong ordering** when timestamps have mixed timezone offsets (`+02:00` vs `+00:00`). ISO 8601 strings only sort correctly lexicographically when timezone offsets are identical. The engine sort methods must parse timestamps to `datetime` for comparison, not rely on lexicographic sort. String storage is correct; string comparison for ordering is not.

### extra='allow' — correct but leaky

`extra='allow'` on the canonical model means Pydantic won't catch typos in frontmatter keys. A user who writes `proirity: needed` gets the default priority while their misspelled key travels silently in extras. This is the correct trade-off — `extra='forbid'` would break on any vendor/future field (`class`, `started`, `completed`, `assignee`, `due`, `estimate` all exist today as extras).

Mitigation: validation of critical constrained fields (status against config-defined statuses, priority against config-defined priorities) must happen in engine methods, not at the Pydantic model layer. The engine already validates status in `move_task` — extend this pattern to all mutation methods.

### File format: keep YAML frontmatter + markdown body

Human-readable, git-diffable, grep-friendly, works with existing tooling. The frontmatter/body split is clean. The parser is robust — it finds only the first `---` after the opening delimiter, so body content containing `---` lines is safe.

Atomic writes via `tempfile.mkstemp` + `Path.replace()` — solid pattern, no changes needed.

### Config round-trips: ruamel.yaml

The `config_loader.py` read-modify-write strategy with `ruamel.yaml` round-trip mode preserving comments and field order is correct. Keep it.

### Activity log: append-only JSONL

The current design is adequate for single-consumer. For multi-consumer (the goal of this project), each log entry needs an `actor` field to distinguish agent vs GUI vs future consumers. Currently, `claim`/`release` actions include the engine's agent name in the `detail` field but `edit`, `move`, `create` do not.

## Key Trade-offs

| Choice | Cost | Avoids |
|--------|------|--------|
| String timestamps | Parse overhead on every sort/comparison | Zero data loss on round-trips; no nanosecond truncation |
| `extra='allow'` on canonical model | Silent carry of misspelled/garbage keys | Silent drop of legitimate vendor/future fields (class, started, completed, etc.) |
| `TaskSummary` as a second model | Two models to maintain in the engine | Ad-hoc hand-built dicts with no schema validation; drift between list and show representations |
| No `file` field on canonical model | MCP adapter must enrich separately | Engine model leaking filesystem implementation details |
| No schema version on task files | Forward migration is manual grep-and-edit | Over-engineering for a single-board single-user system |

## Warnings

1. **Config staleness across engine instances.** `create_task` correctly reloads config to get fresh `next_id`. But `_status_rank()`, `_priority_rank()`, and status validation in `move_task` all use `self._config` cached at construction. If a second consumer (GUI) adds a new status or priority via config, the MCP engine instance won't see it. This is distinct from the D2 concurrency decision — it's a "two long-lived processes with stale cached config" problem, not a concurrent write problem. Recommend: lazy config access or explicit `refresh_config()` for read-only config queries; keep the reload-on-write pattern in `create_task`.

2. **Timestamp sort ordering is currently broken for mixed TZ offsets.** The engine sorts `created`/`updated` fields via string comparison. Legacy Go timestamps have `+02:00` offsets; Python timestamps have `+00:00`. Lexicographic sort of these is wrong. Must parse to `datetime` for sort key computation.

3. **Activity log lacks actor identity for non-claim operations.** The `create`, `edit`, `move` actions log what changed but not who did it. Multi-consumer traceability requires an `actor` field on every entry.

4. **`KanbanTask.file` is always `None`.** A schema field that is never populated is worse than absent — it misleads consumers into thinking the data might be available. Either populate it in the MCP adapter or drop it.

5. **`list_tasks` hand-built dict stripping is fragile.** The `_strip` set in `server.py` is a hardcoded allowlist-via-denylist. If the canonical model gains a new field, it silently passes through to the lean dict unless someone remembers to add it to `_strip`. `TaskSummary` fixes this by making the projection explicit and schema-validated.

## Confidence

**0.85** — High confidence on the canonical model design (single Task + TaskSummary, string timestamps, extra='allow'). Moderate uncertainty on whether `TaskSummary` should derive from `Task` (via field exclusion) or be an independent model — practical testing will resolve this. The timestamp sort bug and config staleness are concrete findings.
