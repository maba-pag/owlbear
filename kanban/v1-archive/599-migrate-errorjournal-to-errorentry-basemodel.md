---
id: 599
title: Migrate ErrorJournal to ErrorEntry BaseModel + JsonlStore
status: archived
priority: needed
created: 2026-03-06T10:23:47.1841901+01:00
updated: 2026-03-06T19:28:28.4648352+01:00
started: 2026-03-06T15:27:08.6035831+01:00
completed: 2026-03-06T19:28:28.4648352+01:00
tags:
    - dry
    - refactor
    - scope:core
depends_on:
    - 465
class: standard
---

## Context
ErrorJournal uses raw dicts + json.dumps instead of Pydantic BaseModel + TypeAdapter. Split from #465 because it requires creating a new model and has rotation logic.

## Acceptance Criteria
- [ ] `ErrorEntry(BaseModel)` created in `error_journal.py` with fields: timestamp (str), error_type (str), tool_name (str), exception_message (str), action_taken (str), attempt_number (int), resolved (bool), session_id (str)
- [ ] `ErrorJournal` inherits `JsonlStore[ErrorEntry]`
- [ ] `log()` method calls `self.append(ErrorEntry(...))` instead of manual json.dumps
- [ ] `_load_all()` removed -- `self.load()` from base class replaces it
- [ ] `query()` operates on `list[ErrorEntry]` with attribute access instead of dict key access
- [ ] `_maybe_rotate()` stays as override -- loads via `self.load()`, writes via TypeAdapter
- [ ] `__init__` passes derived path to `super().__init__(path, ErrorEntry)`
- [ ] All existing tests in `test_error_journal.py` pass (may need minor dict->model updates if tests assert dict structure)
- [ ] `ruff check` clean

## Architecture Notes
- ErrorJournal.__init__ takes `workspace` and derives path -- keep this interface, just call `super().__init__` with the derived path
- Callers of `query()` that expect `dict` return type need audit -- check all call sites
