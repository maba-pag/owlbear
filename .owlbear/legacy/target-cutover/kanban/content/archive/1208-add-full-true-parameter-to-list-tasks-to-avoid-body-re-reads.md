---
id: 1208
title: Add full=True parameter to list_tasks to avoid body re-reads
status: archived
priority: medium
created: 2026-04-30 15:29:06.239755+00:00
updated: 2026-05-02T19:48:52.789248+00:00
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1207
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Avoid body re-reads for callers that need full task objects.

## Files
- engine.py (list_tasks method)

## Change
Add optional `full: bool = False` parameter to list_tasks(). When True, return full Task objects (with body) instead of body-stripped summaries. Callers needing body (pick_tasks, dispatch) use full=True.

## AC
- [ ] list_tasks accepts full parameter
- [ ] full=False returns stripped summaries (default, no regression)
- [ ] full=True returns complete Task objects with body
- [ ] pick_tasks uses full=True
- [ ] Tests cover both modes

## Finding: 5.3

[[2026-05-02]]
## Architecture Review

### Verdict: REJECT → research

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single parameter addition |
| Interface clarity | FAIL | Return type when `full=True` undefined; `TaskFull` already exists but is not referenced |
| Dependency correctness | FAIL | #1209 has no code dependency on this; #1214 doesn't depend on this task at all |
| Module layering | PASS | Stays within engine |
| TDD compliance | PASS | Tests required in AC |
| KISS/YAGNI | FAIL | No current consumer needs `full=True`; speculative API surface |
| Premise challenge | FAIL | Both named callers are wrong (see below) |
| Pattern consistency | FAIL | `TaskFull(TaskSummary)` already exists as the body-bearing projection |
| Security surface | PASS | No new system boundary |
| Single domain | PASS | Engine domain only |

### Rejection Reasons

1. **Premise is factually wrong.** Task claims "Callers needing body (pick_tasks, dispatch) use full=True." Neither caller needs this:
   - `pick_tasks` (engine.py:2306) only accesses `dep_status`, `status`, `id`, `priority`, `title`, `tags` — never `body`
   - `dispatch.py:pick_dispatchable()` bypasses `list_tasks()` entirely — reads full Tasks via N+1 `show_task()` calls

2. **No "body re-reads" exist.** The mtime cache (`_task_cache`) stores full `Task` objects. The `TaskSummary` conversion at engine.py:757-763 is an in-memory `model_dump()` → `model_validate()` projection, not a disk read. The performance claim is unfounded.

3. **`TaskFull` already solves this.** `models.py:576` defines `TaskFull(TaskSummary)` with `body`, `created`, `updated`. The task doesn't reference this existing model.

4. **YAGNI.** No current code path in `list_tasks()` callers (MCP server, Cockpit, `pick_tasks`, `AgentView.list_tasks`) needs body. This is speculative surface.

5. **Dependency chain is unsupported.** #1209 (dispatch constant validation) has no code dependency on `full=True`. #1214 (port gates) depends on #1213 and #1209, not on #1208. When #1214 needs body for TDD/clarity gates, it can use `TaskFull` or the existing cache.

### Challenge Result
Challenger confidence: 0.38 in original. Recommended block. Architect concurs — the premise, consumer evidence, and model-contract analysis all fail.

### Downstream Impact
- #1209 `depends_on: [1208]` — this dependency should be re-evaluated. #1209 validates dispatch constants vs config at startup; no code relationship to `full=True`.
- The real performance hotspot is `dispatch.py:pick_dispatchable()` N+1 `show_task()` — that's #1214's scope, and it can be solved without this task.
[[2026-05-02]]
## Research
- Research doc: .owlbear/research/1208-list-tasks-full-parameter.md
- Sources: 4 studied, 4 high-relevance (all internal codebase)
- Recommendation: Close as invalid — premise factually wrong on all 3 pillars (confidence: 0.95)
- Follow-up tasks created: none (N+1 hotspot already covered by #1214)
- Decision requests: none
- Dependency fix: removed #1208 from #1209 depends_on (spurious)

## Challenge Results
- Challenger: block (architecture review served as challenger)
- Confidence in original: 0.38
- Key challenges: no disk re-reads exist, neither named caller needs body, TaskFull already covers use case
- Researcher response: accepted — all rejection reasons validated against live code

## Verdict
Task premise invalid. "Body re-reads" don't exist (mtime cache holds full Task objects; projection is in-memory). Neither pick_tasks nor dispatch would use full=True. YAGNI. Recommend archival.
[[2026-05-02]]
## Architecture Review (2nd pass)

### Verdict: CLOSE → done (invalid)

Research confirmed all 5 original rejection reasons with 0.95 confidence. No remediation path exists:

1. **Premise invalid** — "body re-reads" don't exist; mtime cache holds full Task objects; projection is in-memory model_dump/validate
2. **No consumer** — pick_tasks never reads body; dispatch bypasses list_tasks entirely
3. **Existing solution** — TaskFull(TaskSummary) already models body-bearing projections
4. **YAGNI** — no current caller needs full=True
5. **Dependency #1207 deleted** — upstream dependency no longer exists

Researcher validated against live code. No follow-up tasks needed (N+1 hotspot already covered by #1214). Spurious #1209 dependency already removed by researcher.

Closing as invalid per research recommendation.
[[2026-05-02]]
## Audit

**Task type:** Invalid/closed — researched and closed without implementation.

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| list_tasks accepts full parameter | N/A — task closed as invalid; no implementation | SKIP |
| full=False returns stripped summaries | N/A | SKIP |
| full=True returns complete Task objects | N/A | SKIP |
| pick_tasks uses full=True | N/A | SKIP |
| Tests cover both modes | N/A | SKIP |

**Rationale for SKIP:** All 5 AC lines describe features for a task whose premise was proven false. Architect rejected → researcher confirmed with 0.95 confidence → architect 2nd pass closed as invalid. No implementation expected.

### Evidence Verified
1. **Research doc exists:** `.owlbear/research/1208-list-tasks-full-parameter.md` — thorough, 4 sources, clear trade-off matrix
2. **Premise invalid (spot-checked):** `_task_cache: dict[str, tuple[int, Task]]` at engine.py:404 — full Task objects, no disk re-reads
3. **#1209 dependency removed:** confirmed `depends_on: []`
4. **#1207 deleted:** confirmed not found in task store
5. **Challenger block accepted:** architecture review served as challenger (confidence 0.38 in original)

### Test Results
- pytest: 3663 passed, 126 failed, 4 skipped (all failures pre-existing, no task-scoped changes)
- vitest: 942 passed, 5 failed (all pre-existing)
- ruff: 3 violations (all pre-existing, unrelated files)
- eslint: 1 warning (pre-existing)
- **No task-specific regressions** — zero code was changed

### Architect Quality: 4/5
Architect properly rejected the task on first review with 5 concrete, code-referenced rejection reasons. Research round-trip confirmed all 5. Self-correction was exemplary. Minor: required a research cycle to fully validate (could have been conclusive at first review given the evidence was in-engine). The *original* AC was premise-flawed (from decomposition), but the architect caught it — that's the job.

### Deduction Breakdown
- AC lines without evidence: 0 deductions (task invalid — AC was never meant to be implemented)
- Lint violations: 0 (pre-existing, not task-scoped)
- AC quality ≤ 3: no (score 4)
- Missing reviewer evidence: 0 (invalid task — no code to review)
- Full-suite failures in task scope: 0 (no code changes)
- Minor: `depends_on: [1207]` metadata not cleaned up despite #1207 deletion → -.01

### Confidence: 0.99
### Action: archive