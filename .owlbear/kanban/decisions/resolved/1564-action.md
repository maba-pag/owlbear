---
task_id: 1564
agent: test-writer
request_type: action
created: '2026-05-15'
response: resolved
resolved: '2026-05-15'
---

## Resolution

Resolved as stale. The target spec `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` already contains the three requested additions:

- `tags behavioral: PDS update event selection narrows visible task cards`
- `(c.2) priority-filter p-select contains no native option children (dual-render falsifiability)`
- `(a.2) task-editor priority p-select contains no native option children (dual-render falsifiability)`

The referenced scratch artifact `.owlbear/scratch/1564-missing-test-additions.ts` is no longer present; the task notes also state the additions were applied and the scratch file removed.

## Underlying Fix

The broader cause was not task-specific: the test-writer path guard allowed `tests/`, `__tests__/`, and `.owlbear/scratch/`, but not Cockpit Playwright E2E specs under `serve/cockpit/web/e2e/`.

That guard has been updated in both live and seed hook copies to allow `e2e/`, with regression tests covering create-file and apply-patch writes to E2E spec paths.

Verification:

- `uv run pytest tests/test_write_guard_hooks.py` -> 26 passed
- `uv run ruff check .owlbear/hooks/deny-src-writes.py seed/.owlbear/hooks/deny-src-writes.py tests/test_write_guard_hooks.py` -> clean
