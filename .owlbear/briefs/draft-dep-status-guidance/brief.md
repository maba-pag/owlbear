# Brief — Add Dep-Status Guidance to start_work()

## Summary

**Problem:** When an agent claims a task via `start_work()` — typically through manual user assignment — it proceeds with no awareness that dependencies are unresolved. The `pick_tasks()` path already filters blocked tasks, but the direct `start_work()` path has no such signal.

**Solution:** After a successful claim, compute `dep_status` inline. If "blocked", return a directive guidance string listing unresolved dep IDs and asking the agent to confirm intent with the user.

**Tier:** Tool | **Scope:** ~15 LoC in `agent_view.py` | **Type:** existing-feature/refactor

## Scope & Constraints

- Soft gate only — task is claimed successfully; guidance is advisory
- "blocked" status only (redirect dropped — means deps are done)
- Uses existing `SingleTaskResponse.guidance` field — no schema changes
- Uses existing `_compute_dep_status()` — no new engine primitives
- Inline dep iteration (not extracted helper) — 2 consumers below extraction threshold
- No MCP tool surface changes (schema unchanged; new behavioral output documented)
- No agent instruction changes — directive guidance at point-of-action suffices

## Design

**Placement:** After successful `engine.start_work()` claim, before returning.

**Logic:**

1. Iterate `task.depends_on`, calling `engine.show_task(dep_id)` per dep
2. Catch `(FileNotFoundError, CorruptionError, ValueError, KeyError)` with `continue`
3. Partition into `active_ids: set[int]` and `archived_reasons: dict[int, str | None]`
4. Call `engine._compute_dep_status(task, active_ids=..., archived_reasons=...)`
5. If `"blocked"`: format guidance string with dep IDs
6. Pass guidance to `_to_single_response(task, guidance=guidance)`

**Guidance format:**

```
⚠️ This task has unresolved dependencies (IDs: 42, 78). Review and confirm with the user that starting this work is intentional.
```

**Non-goals:** dep_status field on SingleTaskResponse, per-dep detail, redirect handling, helper extraction.

## Acceptance Criteria

**AC1:** `start_work()` on a task with dep_status=="blocked" returns a `SingleTaskResponse` where `guidance` contains exactly one string matching the format `"⚠️ This task has unresolved dependencies (IDs: {comma-separated ints}). Review and confirm with the user that starting this work is intentional."`

**AC2:** `start_work()` on a task with no deps, or with all deps resolved, returns `guidance == []` (unchanged behavior).

**AC3:** `start_work()` on a task where dep lookup raises any of `(FileNotFoundError, CorruptionError, ValueError, KeyError)` for a dep silently continues past that dep (existing resilience pattern).

**AC4:** The MCP `start_work` tool handler passes guidance through verbatim (MCP-layer test with exact-value assertion).

**AC5:** A consolidation test asserts that the exception tuple in `start_work()` matches the one in `show_task()` for dep lookups.

## Test Strategy

- Unit tests in `serve/kanban/tests/` covering AC1-AC3 (dep-blocked, no-deps, resolved-deps, corrupt-dep scenarios)
- MCP-layer integration test in `serve/mcp-kanban/tests/` covering AC4
- Consolidation test (matches `test_consolidate_helpers.py` pattern) covering AC5
- No E2E changes needed (no UI, no agent instruction changes)

## Operational Notes

- Guidance message format is wire contract once shipped — format changes require versioning consideration
- `create_task`, `edit_task`, `end_work`, and `_skip_transition_guidance()` already produce guidance — this follows the same pattern
- The `h-mcp-kanban` skill's guidance-producing operations table should be updated post-ship to include `start_work`
