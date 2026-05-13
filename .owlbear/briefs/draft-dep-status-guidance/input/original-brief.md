# Dep-Status Guidance in start_work

## Problem

`pick_tasks` correctly filters out dep-blocked tasks from dispatch. But `start_work` does not check `dep_status` — an agent given a task ID directly (by an orchestrator, user, or explicit instruction) can claim and work on a task whose dependencies aren't resolved, with no warning. This leads to wasted effort or rework.

## Proposed Change

Add a dep-status check in `agent_view.start_work()` that computes `dep_status` and includes guidance if the task has unresolved dependencies. This is a **soft gate** (guidance warning), not a hard block — the task is still claimable.

### Guidance format

When `dep_status == "blocked"`, the `start_work` response should include a guidance string listing unresolved dependencies with their current statuses:

> "⚠ Unresolved dependencies: #1230 (status: in-progress), #1231 (status: todo). Work may be premature — consider waiting for these to complete."

When `dep_status == "redirect"`, guidance should note that a dependency was archived with a non-completed reason:

> "⚠ Dependency #1230 was archived as 'deprecated' (replaced by #1235). Review archival_refs before proceeding."

### Implementation sketch

In `agent_view.start_work()`, after the successful claim:

1. Compute `dep_status` using the existing `self.engine._compute_dep_status()` method
2. If `dep_status` is `"blocked"` or `"redirect"`, resolve each dep ID to get its status/archival info
3. Format a guidance string with dep IDs and their states
4. Append to the response's `guidance` list

### Scope

- ~10-15 lines of code in `agent_view.py`
- No schema changes, no new fields, no config changes
- No breaking changes to `start_work` API (guidance is already part of `SingleTaskResponse`)
- Backward-compatible: tasks without deps produce no guidance (same as today)

### Why not hard-block?

Users sometimes intentionally start work on dep-blocked tasks:
- Dep is effectively done but not formally archived yet
- Parallel work on related tasks is intended
- User override via explicit task ID assignment

A hard block would require an escape hatch mechanism, adding complexity for little gain. Guidance preserves agent autonomy while surfacing the risk.
