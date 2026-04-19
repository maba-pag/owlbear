# Architect Stance — Critic Debate Log

## Cycle 1

**Critic confidence: 0.37 — Reject**

### Challenges

1. **Critical: `sweep` leaks implementation/storage concerns.** Server already auto-runs sweep. Meanwhile `valid_transitions` was skipped despite M3 endorsement. → **Accepted.** Replaced `sweep` with `list_transitions`.

2. **Moderate: `ids` filter semantics muddled.** Auto-include-archived while other filters AND-combine creates silent drops. → **Accepted.** Simplified to ID-lookup mode: `ids` ignores all other filters.

3. **Critical: Section param underspecified for repeated headings.** `## Review Evidence` appears multiple times. First/last/all never specified. → **Accepted.** Specified: return ALL matching sections in document order with `##` delimiters preserved. Guidance includes count.

4. **Critical: `completed` via `move_task` unrestricted.** Any caller can claim `completed`, erasing auditor signal. → **Accepted.** Gated: `completed` via `move_task` only valid from `done` status.

5. **Moderate: Batch-create internal contradiction.** Prompt says "no batch-internal deps" but spec allows position-based resolution. → **Accepted.** Settled: no batch-internal deps. Pre-existing IDs only.

6. **Moderate: Coherence argument applied selectively.** Status overlap removed but block overlap and `_work` naming kept without justification. → **Accepted.** Added explicit justification for both.

7. **Blind spot: `pick_tasks` dispatch shape mismatch.** Returns `{task_id, status}` but orchestration skill consumes `id, status, priority, title, tags`. → **Accepted.** Widened dispatch projection.

8. **Blind spot: Relational archival reasons without links.** `deprecated`/`duplicate` imply a related task but schema has no field for it. → **Accepted.** Added `archival_ref: int | null`.

---

## Cycle 2

**Critic confidence: 0.41 — Reject**

### Challenges

1. **Critical: `create_tasks` "2 calls replaces 20" claim fails for multi-layer graphs.** Planner decomposes into layered deps; deeper than roots+1 breaks the 2-call claim. → **Accepted (partial).** Fixed justification: D calls per dependency layer vs N individual calls. Typical 3-layer/20-task = 3 calls vs 20.

2. **Critical: `pick_tasks` field name `task_id` vs `id` mismatch persists.** → **Accepted.** Renamed `task_id` → `id` in DispatchEntry.

3. **Moderate: `ids` mode silently ignores other filters.** → **Accepted.** Changed to error-on-conflict: `ToolError` when `ids` is combined with non-default filters.

4. **Moderate: Section selector doesn't model "latest" use case.** Retry handling needs most recent `## Review Evidence`. → **Acknowledged.** V1 returns all; callers split on `##`. Noted `section_index` as V2.

5. **Moderate: `completed` gating forces less truthful reason; immutability makes it permanent.** → **Rejected.** `completed` means pipeline-complete. Non-done tasks are not completed. 2-call path (advance to done, then archive) is proper sequencing.

6. **Moderate: `archival_ref` only partially earns cost because it's optional.** → **Rejected.** Optional > absent. Required would create friction when target ID is unknown.

7. **Moderate: `list_transitions` is speculative.** No concrete current workflow needs it. → **Accepted.** Dropped `list_transitions`. Surface reduced to 10 tools.

8. **Moderate: 11-tool surface not fully justified.** Two additions have weak backing. → **Partially accepted.** Dropped `list_transitions` (10 tools). `create_tasks` and `list_sessions` both have concrete consumers.

### Blind spots acknowledged

- Silent omission of missing IDs in `ids` lookup: callers compare returned vs requested. V1 acceptable.
- "Latest section" use case: documented as V2 `section_index` consideration.
- No concrete current workflow for `list_transitions`: dropped from surface.
