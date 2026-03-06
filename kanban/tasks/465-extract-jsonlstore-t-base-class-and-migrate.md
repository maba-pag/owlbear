---
id: 465
title: Extract JsonlStore[T] base class and migrate UsageTracker + EventStore
status: archived
priority: needed
created: 2026-03-04T07:37:45.4384051+01:00
updated: 2026-03-06T19:28:09.453234+01:00
started: 2026-03-06T10:04:54.9658522+01:00
completed: 2026-03-06T19:28:09.453234+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:core
class: standard
---

## Context

Research: docs/jsonl-store-base-class-research.md
Duplication: __init__, path, append, load are identical across UsageTracker, EventStore (~25 lines each).

## Acceptance Criteria

- [ ] `JsonlStore[T]` generic base class exists at `src/owlbear/core/jsonl_store.py`
- [ ] Constructor: `__init__(self, path: Path, record_type: type[T]) -> None` stores path and creates `TypeAdapter[T]`
- [ ] `path` property returns `self._path`
- [ ] `append(record: T) -> None`: `mkdir(parents=True, exist_ok=True)` + `TypeAdapter.dump_json` + `open('a')` + `write(line + '\n')`
- [ ] `load() -> list[T]`: return `[]` if file missing; `read_text().strip().splitlines()` + `TypeAdapter.validate_json` per line
- [ ] `UsageTracker` inherits `JsonlStore[UsageRecord]`, removes duplicated __init__/path/append/load; keeps `query()`, `summary()` as-is
- [ ] `EventStore` inherits `JsonlStore[ObservabilityEvent]`, removes duplicated __init__/path/append/load; keeps `query()`, `summary()`, `tool_stats()` as-is
- [ ] All existing tests in `test_usage_tracker.py`, `test_observability_hook.py` pass unchanged
- [ ] `ruff check` clean

## Architecture Notes

- Follow existing TypeAdapter pattern already used by both stores (module-level `_adapter`)
- TypeAdapter created once in `__init__` from `record_type`, stored as `self._adapter`
- ErrorJournal migration is a __separate task__ (#599) because it requires creating an `ErrorEntry` BaseModel and has rotation logic
- File location: `src/owlbear/core/` because it's infrastructure used by both `core/` and `memory/`
