# TASK_COMPLETE Audit-Map Advisory Worker — Implementation Research

> **Owning task:** #954 - Implement TASK_COMPLETE audit-map advisory worker pilot
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #954 asks how to implement the audit-map advisory worker pilot selected
in the parent research (#949, `docs/research/hook-triggered-background-worker-pilot.md`
§3.2). The worker fires on `TASK_COMPLETE` for successful tasks, writes a
scratch-only audit-map advisory, and makes zero mutations to kanban, claims,
docs, or source code. All infrastructure exists: `HookWorkerSupervisor` (#953),
`HookRegistry`, config flag patterns, and the `RetrospectiveHook` consumer
pattern. The open question is implementation approach, gating model, artifact
format, and test strategy. [S1, S3, S4, S7]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Parent research `docs/research/hook-triggered-background-worker-pilot.md` | 1.0 | Selected audit-map as best pilot (§3.2), recommended supervised task set (§3.3), defined 6 safety gates (§3.4) |
| S2 | ruvnet/ruflo README (`github.com/ruvnet/ruflo`) | .80 | 12 context-triggered workers: `audit` (security scanning), `map` (codebase structure mapping), auto-trigger patterns |
| S3 | Python asyncio task docs (`docs.python.org/3/library/asyncio-task.html`) | .90 | `create_task()` strong-reference lifecycle, `Semaphore` bounded concurrency, cooperative cancellation |
| S4 | OwlBear `hook_worker_supervisor.py` | 1.0 | `schedule(awaitable)` with semaphore gating, `shutdown()` cancel+await, strong-reference set |
| S5 | OwlBear `retrospective_hook.py` | 1.0 | Existing TASK_COMPLETE consumer: `__call__` filters outcome=="success", `_LazyCoroutine`, `supervisor.schedule()` |
| S6 | OwlBear `config.py` | 1.0 | Feature flag pattern: `bool = Field(default=False)`, `OWLBEAR_` prefix, `get_settings()` singleton |
| S7 | OwlBear `bootstrap/__init__.py` + `bootstrap/hooks.py` | 1.0 | Wiring: `_wire_post_model_hooks()` creates supervisor, `build_hooks()` does conditional registration |

## 3. Analysis

### 3.1 Implementation Approach

| Approach | KISS | Reuse | Isolation | Confidence |
|----------|------|-------|-----------|:----------:|
| **A. New standalone hook class** | High | Follows RetrospectiveHook pattern | Full — own module, own tests | **.85** |
| B. Extend RetrospectiveHook | Medium | Shares existing class | Low — adds branching to existing logic | .55 |
| C. HookReactionRouter policy | High | Reuses router | Low — router is for notify/retry/escalate, not artifact generation | .40 |

**Winner: A — New standalone class.** RetrospectiveHook is purpose-built for
lesson extraction and has its own eligibility rules (priority, rejection count).
Adding audit-map branching would violate SRP. The HookReactionRouter is for
fire-and-forget reactions (notify, retry, escalate), not for artifact-producing
workers that need filesystem access. A dedicated class follows the same pattern
but stays isolated. [S1, S5]

### 3.2 Gating Model

AC #2 requires both config flag and task tag. This matches two existing patterns:

| Gate | Precedent | Implementation |
|------|-----------|----------------|
| Config flag | `lessons_injection_enabled`, `session_memory_enabled` | `audit_map_worker_enabled: bool = Field(default=False)` |
| Task tag | `resolve_rigor_profile()` extracts `rigor:*` tags | Check for `worker:audit-map` in task tags |

Both gates are evaluated in `__call__` before scheduling work. The config flag
is checked first (fast reject), then the tag is extracted from the task data.
The tag requires reading the task file to get its tags — the `task_id` is
already in `TaskCompleteData`. [S1 §3.4, S6]

### 3.3 Artifact Format

| Format | Simplicity | Parseable | Convention Fit | Confidence |
|--------|------------|-----------|----------------|:----------:|
| **Markdown scratch file** | High | By humans and agents | `docs/scratch/{task-id}-audit-map.md` | **.90** |
| JSON scratch file | Medium | By code | Not conventional for advisories | .60 |
| Pydantic model → JSON | Low | By code | Over-engineered for advisory-only output | .40 |

**Winner: Markdown scratch file.** The `docs/scratch/` convention is
established (gitignored, task-scoped naming). Advisory content is for human
and agent consumption, not programmatic parsing. KISS wins. [S1 §3.4]

### 3.4 Bootstrap Wiring

Two options for supervisor sharing:

| Wiring | Pro | Con | Confidence |
|--------|-----|-----|:----------:|
| **Share existing supervisor** | Zero new objects, tested path | Couples concurrency budget | **.80** |
| Dedicated supervisor | Independent concurrency | Extra object, extra shutdown | .65 |

**Winner: Share existing supervisor.** The supervisor already has a concurrency
semaphore (default=1). Since both RetrospectiveHook and audit-map are
TASK_COMPLETE consumers with low duty cycle, sharing is fine. If concurrency
becomes an issue later, splitting is a one-line change. YAGNI. [S3, S4]

### 3.5 Safety Boundaries (from parent research §3.4)

The 6 gates from the parent research map to concrete implementation:

| Gate | Implementation | Test Strategy |
|------|----------------|---------------|
| 1. Success-only trigger | `if data["outcome"] != "success": return` | Unit test: call with outcome="failure" → no-op |
| 2. Config flag + task tag | `if not settings.audit_map_worker_enabled: return` + tag check | Unit test: flag off → no-op; missing tag → no-op |
| 3. Supervised background | `self._supervisor.schedule(coroutine)` | Unit test: mock supervisor, verify `schedule()` called |
| 4. Scratch-only artifact | Write to `docs/scratch/{id}-audit-map.md` | Unit test: verify path prefix; integration test: check file exists |
| 5. No board mutations | No kanban-md calls, no file writes outside scratch | Unit test: mock filesystem, verify only scratch path written |
| 6. Non-goals excluded | No auto-created tasks, no doc edits, no source writes | Negative tests: verify no kanban create, no src/ writes |

### 3.6 Notification

The optional notification (AC #3) should use the existing `ChannelPlugin`
interface if a channel is available. A single advisory message like
"Audit-map advisory written to docs/scratch/{id}-audit-map.md" is sufficient.
If no channel is available, the worker completes silently. [S5]

## 4. Recommendation (.85 confidence)

Implement a standalone `AuditMapAdvisoryHook` class following `RetrospectiveHook`
patterns: `__call__` filters on outcome=="success", checks config flag and tag,
delegates to `supervisor.schedule()`. The coroutine reads the task file for
context, generates a markdown advisory, writes to `docs/scratch/{id}-audit-map.md`,
and optionally sends a channel notification. Register in `build_hooks()` behind
the `audit_map_worker_enabled` config flag, sharing the existing supervisor.

**Risk:** Low. Advisory-only output, scratch-only writes, gated behind opt-in
config + tag. No pipeline mutations. The only dependency is filesystem access to
`docs/scratch/` and read-only access to `kanban/tasks/`.

## 5. Follow-up Tasks

Tasks created at `ideation` status per research workflow.

```
kanban\kanban-md.exe create "RED tests: AuditMapAdvisoryHook eligibility and safety" --priority needed --status ideation --tags "phase-6,test,hooks,type:test" --body "## Acceptance Criteria\n- [ ] Test: hook no-ops when outcome != 'success'\n- [ ] Test: hook no-ops when config flag is False\n- [ ] Test: hook no-ops when task lacks 'worker:audit-map' tag\n- [ ] Test: hook calls supervisor.schedule() when all gates pass\n- [ ] Test: artifact written only to docs/scratch/{id}-audit-map.md\n- [ ] Test: no kanban-md calls, no src/ writes, no docs/ writes outside scratch\n- [ ] Test: optional channel notification sent when channel available\n- [ ] Test: no notification when channel unavailable\n\nSee docs/research/task-complete-audit-map-advisory-worker.md for design.\nDepends on #954 (research)."
```

```
kanban\kanban-md.exe create "Implement AuditMapAdvisoryHook class" --priority needed --status ideation --tags "phase-6,hooks,type:build" --body "## Acceptance Criteria\n- [ ] New module src/owlbear/core/audit_map_hook.py with AuditMapAdvisoryHook class\n- [ ] __call__ filters: outcome=='success', config flag, 'worker:audit-map' tag\n- [ ] Delegates to supervisor.schedule() for background execution\n- [ ] Writes markdown advisory to docs/scratch/{task-id}-audit-map.md\n- [ ] Optional ChannelPlugin notification on completion\n- [ ] No mutations to kanban board, claims, docs (non-scratch), or source\n- [ ] Config flag: audit_map_worker_enabled (default=False) in OwlBearSettings\n- [ ] Register in build_hooks() behind config flag, sharing existing supervisor\n- [ ] All RED tests from test-writer task pass\n\nSee docs/research/task-complete-audit-map-advisory-worker.md for design.\nDepends on RED tests task."
```
