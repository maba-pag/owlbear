# Research Notes — Dep-Status Guidance in start_work

## Verified Findings

1. **`agent_view.start_work()`** (line 962) calls `self.engine.show_task()` to check archived status before claiming, then `self.engine.start_work()` to claim. Neither computes `dep_status`.

2. **`agent_view.show_task()`** (line 214) already computes `dep_status` by iterating `task.depends_on`, looking up each dep via `engine.show_task()`, partitioning into `active_ids` and `archived_reasons`, then calling `engine._compute_dep_status()`. This is the proven pattern (~10 LoC of dep iteration).

3. **`_to_single_response()`** (line 54) already accepts an optional `guidance: list[str]` parameter. `start_work` currently calls it with no guidance: `return self._to_single_response(task)`.

4. **`_compute_dep_status()`** (engine line 663) returns `None` (no deps), `"ok"` (all resolved), `"blocked"` (active or missing deps), or `"redirect"` (deps archived with non-completion reason). Only needs `active_ids: set[int]` and `archived_reasons: dict[int, str | None]`.

5. **`start_work` already has the task object** via `self.engine.show_task(str(task_id))` (assigned to `task_record`) which carries `depends_on`. The dep iteration can happen right after this call, before or after claiming.

6. **Guidance pattern already exists:** `_skip_transition_guidance()` produces ⚠ warnings for status skips. Same pattern applies here — compute condition, format string, pass to `_to_single_response`.

7. **`pick_tasks()`** (line 311+) already filters `dep_status="blocked"` tasks from dispatch. The gap is only in the direct `start_work` path.

## Candidate Implications

- The dep iteration in `show_task` reads each dep from disk individually (`engine.show_task(str(dep_id))`). For tasks with many deps this could be slow — but kanban tasks rarely have >3 deps, so this is not a practical concern.
- The simplifier's "~5 LoC" estimate is close: compute dep_status from `task_record.depends_on`, check result, format one guidance string, pass to `_to_single_response`. The dep iteration itself is ~8-10 LoC (matching the existing `show_task` pattern), so total is ~12-15 LoC including the guidance formatting.
- The guidance text should include dep IDs so the agent can look them up if needed. Format: `"⚠ This task has unresolved dependencies (IDs: 42, 78). Review and confirm with the user that starting this work is intentional."`

## Open Research Questions

- Should the dep_status computation be extracted into a shared helper (used by both `show_task` and `start_work`) to avoid duplication? This is a Phase 2 implementation decision, not a discovery question.
- What happens if a dep lookup fails (CorruptionError, ValueError)? The `show_task` pattern silently `continue`s past failures. Same behavior is appropriate here.
