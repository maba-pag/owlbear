---
id: 1236
title: Research — extend SSE to decisions and activity polling
status: archived
priority: medium
created: 2026-04-30 16:48:43.009769+00:00
updated: 2026-05-03T23:26:33.815775+00:00
tags:
- cockpit
- architecture
- research
parent:
depends_on:
- 1233
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Investigate extending the SSE /api/events stream to cover decisions polling (currently 60s) and activity/session data. Requires watching decisions directory and activity.jsonl in addition to tasks dir. See .owlbear/research/1233-realtime-cockpit-updates.md
[[2026-05-01]]
## Planning

Created 3 follow-up subtasks at research status:

| ID | Title | Tags | Priority | Deps |
|----|-------|------|----------|------|
| #1262 | Extend SSE watcher to recursive kanban_dir with typed multi-surface events | cockpit, backend | someday | #1234 |
| #1263 | Wire usePendingDRs to SSE decisions-changed early-refetch | cockpit, frontend | someday | #1235, #1262 |
| #1264 | Wire ActivityTab to SSE activity-changed live updates | cockpit, frontend | someday | #1235, #1262 |

Dependency graph:
```
#1234 → #1262 (backend multi-surface watcher)
#1235 ──┬──→ #1263 (decisions early-refetch)
#1262 ──┘
#1235 ──┬──→ #1264 (activity live updates)
#1262 ──┘
```

All tasks parented under #1236.
[[2026-05-01]]
## Research

**Key findings:** Multi-surface SSE extension is feasible via recursive `awatch(kanban_dir)` with path-based event classification. Three typed invalidation events: `tasks-changed`, `decisions-changed`, `activity-changed`. Critical design revision from challenger: SSE supplements (not replaces) decisions/activity polling — avoids stale-data bug when paths don't exist at subscribe time.

**Challenge outcome:** reconsider (0.29 confidence in original). Challenger identified critical stale-data contradiction (pause polling + skip missing paths), authority drift (expanding #1234 scope without approval), frontend delta undercount, and scan invalidation gap. All addressed: switched to recursive watch, made SSE supplementary for non-tasks surfaces, recommended separate implementation task, acknowledged frontend dependency chain. Revised confidence: 0.72.

**Trade-off matrix:** See .owlbear/research/1236-extend-sse-decisions-activity.md §3.1 (watch architecture), §3.5 (late-path handling), §3.9 (scope strategy).

**Classification:** T1 — autonomous. Extension follows approved SSE architecture from #1233. No new capabilities, same transport, same invalidation model.

**Follow-up tasks:** #1262 (backend watcher extension), #1263 (decisions SSE wire-up), #1264 (activity SSE wire-up).

**Doc:** .owlbear/research/1236-extend-sse-decisions-activity.md
[[2026-05-03]]
## Research

**Validation pass (2026-05-04):** Existing research doc and follow-up tasks confirmed current. All follow-up implementation tasks archived:
- #1262 (backend multi-surface watcher) — archived
- #1263 (decisions SSE wire-up) — archived
- #1264 (activity SSE wire-up) — archived, with subtasks #1276, #1277, #1278 also archived

Research gate checklist satisfied. No codebase changes invalidate findings. Advancing to backlog.
[[2026-05-03]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research coordination — investigate SSE extension feasibility |
| Interface clarity | PASS | Research deliverables clear: doc + follow-up tasks |
| Dependency correctness | PASS | #1233 (parent research) archived/done |
| Module layering | N/A | No code produced |
| TDD compliance | PASS | Non-impl task, tagged `research` |
| KISS/YAGNI | PASS | Research scope appropriate |
| Premise challenge | PASS | Research completed its purpose (doc produced, subtasks decomposed) |
| Pattern consistency | PASS | Standard research→decomposition flow |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | Cockpit SSE architecture only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- All AC: (td:0) — research doc production, no testable code
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `research` tag for non-impl pass-through. Research complete (doc at .owlbear/research/1236-extend-sse-decisions-activity.md), all subtasks archived. Advancing to todo.
[[2026-05-03]]
## Test-Writer Notes
- Non-implementation task (tagged `research`) — no tests applicable.
- All AC lines annotated (td:0): research doc production, follow-up task decomposition, no testable Python interfaces.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body includes Test-Writer pass-through note for non-impl routing.
- Tests: not applicable (td:0 research task).
- Lint: not applicable.
- Evidence summary: Research doc exists at .owlbear/research/1236-extend-sse-decisions-activity.md; implementation follow-up tasks were already archived.
- Fixes applied: none.
[[2026-05-03]]
## Review Evidence
### Test Results
- td:0 research task; no task-scoped executable tests apply.
- quality-runner attempt: input error. `mode=scoped` rejected `test_paths=[]` / `lint_paths=[]`, so no pytest or ruff measurement was executed for this non-code no-op review.

### Lint: not applicable
- No lintable source files were changed for this task.
- quality-runner cannot currently express the `w-code-review` td:0 lint-only no-op shape for a non-code task.

### Coverage: not applicable
- td:0 non-implementation research task; no touched runtime module to measure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. No `TestFromAC_*` classes exist for this td:0 research task.

#### Security Review
- No issues in scope. No code changes, no new dependencies, and no boundary-handling changes were introduced by this task.

#### Test Integrity
- Skipped. No task-scoped tests exist.

#### Test Quality
- Skipped. No task-scoped tests exist.

#### Data Safety
- No issues in scope. This task's deliverables are research artifacts and kanban state only.

#### Implementation-Aware Gaps
- Research artifact validation is incorrect. The task claims all follow-up implementation tasks are archived, but live board state contradicts that claim.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Prior `## Review Evidence` sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Archived board lookups confirm `#1262` and `#1263` are archived.
- `#1264` is still a live task, so the parent roll-up note is stale rather than fully validated.
- quality-runner has a td:0/non-code contract gap: scoped mode requires non-empty `test_paths`, which blocks the canonical lint-only no-op requested by `w-code-review`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Research doc production | `.owlbear/research/1236-extend-sse-decisions-activity.md:1` exists with the task research artifact title. | None (td:0) | PASS |
| Follow-up task decomposition | `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:30`, `:31`, `:32` enumerate follow-up tasks `#1262`, `#1263`, `#1264`; live board state resolves those task IDs. | None (td:0) | PASS |
| `Validation pass (2026-05-04): Existing research doc and follow-up tasks confirmed current. All follow-up implementation tasks archived` | Claim is recorded at `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:61` and `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:64`, but `.owlbear/kanban/tasks/1264-wire-activitytab-to-sse-activity-changed-live-updates.md:4` still shows `status: todo`. The same false completion state is repeated at `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:94`. | None (td:0) | FAIL |

### Deductions
- -0.26: Validation/confirmation claim is materially false against live child-task state.
- -0.08: Architecture section repeats the same stale `all subtasks archived` conclusion.
- -0.04: Canonical td:0 quality-runner no-op could not be executed because the subagent contract rejects empty scoped inputs.

### Confidence: 0.62
### Verdict: FAIL
### Action: Reject to `backlog`.

Required follow-up:
- Reconcile the parent research task with actual child-task state before it re-enters review. Either archive `#1264` if complete or update the parent validation/body sections so they no longer claim all follow-up implementation tasks are archived.

### Post-task Reflection
- Live child-task lookup was necessary; the parent roll-up note overstated completion.
- td:0 non-code reviews currently expose a mismatch between `w-code-review` and `quality-runner` input requirements.
- For research roll-up tasks, stale validation text is a contract defect in the artifact itself, not just a note-quality issue.
[[2026-05-03]]

## Reconciliation (re-review cycle)

Reviewer rejection (2026-05-03) was correct: body claimed "all follow-up implementation tasks archived" but #1264 is at `todo` (not archived). Corrected state:

| Child | Status |
|-------|--------|
| #1262 | archived ✓ |
| #1263 | archived ✓ |
| #1264 | `todo` — all constituent subtasks (#1276, #1277, #1278) archived; task is flowing through remaining pipeline as a planning-container closeout |

Research task's own deliverables (research doc + decomposition) remain complete. The false validation claim was a roll-up note error, not a missing deliverable.

## Architecture Review (cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research coordination — doc + decomposition |
| Interface clarity | PASS | Deliverables: research doc, follow-up tasks |
| Dependency correctness | PASS | #1233 archived/done |
| Module layering | N/A | No code produced |
| TDD compliance | PASS | Non-impl, tagged `research` |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | Research purpose fulfilled |
| Pattern consistency | PASS | Standard research→decomposition flow |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | Cockpit SSE architecture |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- All AC: (td:0) — research doc production, no testable code
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Reconciled false validation claim against live child-task state (#1264 at todo, not archived). Research deliverables confirmed complete. `research` tag present for non-impl pass-through. Advancing to todo.

[[2026-05-03]]
Architecture Review (cycle 2): Reconciled false validation claim — #1264 is at todo (not archived), all its subtasks are archived and work complete. Research task's own deliverables (doc + decomposition) confirmed done. Tagged `research` for non-impl pass-through. All td:0. Advancing to todo.
[[2026-05-03]]
## Test-Writer Notes
- Retry cycle: no test changes needed.
- Reviewer Required Follow-up was body reconciliation only (no missing tests).
- Reconciliation already performed by architect in cycle 2 (false "all archived" claim corrected, #1264 live state acknowledged).
- All AC lines remain td:0 (research doc production, follow-up decomposition — no testable Python interfaces).
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body includes Test-Writer non-impl pass-through context.
- Tests: not applicable (td:0 research task).
- Lint: not applicable.
- Coverage: not applicable.
- Evidence summary: Deliverables are research artifact and task decomposition only; builder implementation work is out of scope.
- Files changed: none.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner td:0 no-op report: `passed: 0`, `failed: []`, `skipped: 0`.
- No task-scoped pytest or ruff commands were applicable for this non-implementation research task; quality-runner returned the canonical clean no-op state (`clean: true`, `violations: []`, `errors: none`).

### Lint: clean
- quality-runner reported `clean: true` with no violations.
- No lintable source files were changed in this task scope.

### Coverage: not applicable
- td:0 research task; no touched runtime module to measure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. No `TestFromAC_*` classes exist for this td:0 research task.

#### Security Review
- No issues in scope. No code changes, dependency changes, or new boundary-handling logic were introduced by this task.

#### Test Integrity
- Skipped. No task-scoped tests exist.

#### Test Quality
- Skipped. No task-scoped tests exist.

#### Data Safety
- No issues in scope. Deliverables are the research artifact and kanban task decomposition/state only.

#### Implementation-Aware Gaps
- No remaining gap.
- The first-cycle defect is documented in `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:61` and `:94`, but it is explicitly reconciled later in the same task at `:178`, `:180`, `:184`, `:185`, `:186`, `:216`, and `:219`.
- The reconciled child-state table matches live board state: `.owlbear/kanban/archive/1262-extend-sse-watcher-to-recursive-kanban-dir-with-typed-multi-surface-events.md:5` = `status: archived`; `.owlbear/kanban/archive/1263-wire-usependingdrs-to-sse-decisions-changed-early-refetch.md:4` = `status: archived`; `.owlbear/kanban/tasks/1264-wire-activitytab-to-sse-activity-changed-live-updates.md:4` = `status: todo`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Prior `## Review Evidence` sections | 1 |
| Approach variation | N/A — retry was reconciliation/pass-through, not a repeated code fix |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Historical lines `:61` and `:94` still preserve the original stale claim, but the later reconciliation section is explicit and accurate; in append-only task history this is corrective context, not an unresolved defect.
- `#1264` remains `todo` because it is a planning-container closeout, even though its subtasks are archived.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Research doc production | `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:57` points to `.owlbear/research/1236-extend-sse-decisions-activity.md`, and `.owlbear/research/1236-extend-sse-decisions-activity.md:1` exists with the expected research artifact title. | None (td:0) | PASS |
| Follow-up task decomposition | `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:30`, `:31`, and `:32` define `#1262`, `#1263`, and `#1264`; live child-task state is evidenced by `.owlbear/kanban/archive/1262-extend-sse-watcher-to-recursive-kanban-dir-with-typed-multi-surface-events.md:5`, `.owlbear/kanban/archive/1263-wire-usependingdrs-to-sse-decisions-changed-early-refetch.md:4`, and `.owlbear/kanban/tasks/1264-wire-activitytab-to-sse-activity-changed-live-updates.md:4`. | None (td:0) | PASS |
| Re-review reconciliation of the stale archived-state claim | `.owlbear/kanban/tasks/1236-research-extend-sse-to-decisions-and-activity-polling.md:178`, `:180`, `:184`, `:185`, `:186`, `:216`, and `:219` explicitly correct the earlier false claim and acknowledge `#1264` as `todo`; those statements match live board state. | None (td:0) | PASS |

### Deductions
- -0.03: Earlier append-only sections still contain the superseded stale archived-state claim, even though the later reconciliation section corrects it unambiguously.

### Confidence: 0.95
### Verdict: PASS
### Action: Advance to `docs`.

### Post-task Reflection
- The decisive evidence was the later reconciliation section, not the earlier stale roll-up note.
- td:0 research reviews still require live child-task verification; the no-op quality-runner report is necessary process evidence but not sufficient on its own.
- Append-only kanban history can preserve earlier mistakes as long as a later section explicitly supersedes them and matches the live board.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Pure research task; no behavior/API/CLI/config changes. No README or guide references this SSE research area. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` §"Extend SSE to Decisions and Activity (Task #1236)" (lines 57–62) documents watchfiles awatch API and sse-starlette typed events attribution. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1236-extend-sse-decisions-activity.md` exists, linked from task body. Follow-up tasks #1262 (archived), #1263 (archived), #1264 (todo/planning container) all present. |
| 5 | Diagram maintenance (describes match) | No | N/A | No code files changed; no diagram `describes` glob matches `.owlbear/research/**`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope doc candidates. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1236-extend-sse-decisions-activity.md` | IN | Verified (exists, linked, complete) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-05-03]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc production | `.owlbear/research/1236-extend-sse-decisions-activity.md` exists, complete, references task #1236, sources documented | PASS |
| Follow-up task decomposition | #1262 (archived), #1263 (archived), #1264 (todo, planning container with all subtasks #1276/#1277/#1278 archived) | PASS |
| Reconciliation of stale claim | Body sections at lines 178-219 correctly acknowledge #1264 at todo, matching live board state | PASS |

### Test Results
- pytest: 772 passed, 20 failed (all in unrelated tasks: #1234, #1015, #1181, #1195), 4 skipped. Zero failures in task scope (no code changes).
- vitest: 950 passed, 13 failed (all in #1227, #966 Shell tests). Zero in scope.
- ruff: 1 pre-existing T201 violation, not from this task.

### Architect Quality: 4/5
Research scope was clear (investigate SSE extension for decisions/activity). Deliverables well-defined implicitly (doc + decomposition). Minor: no explicit AC lines in original task body, but research convention suffices.

### Deduction Breakdown
- Historical stale "all archived" claim preserved in append-only body (reconciled later): -0.01

### Confidence: 0.99
### Action: Archive

### Upstream Commits
- `e123aef8` research(#1236): extend SSE to decisions and activity polling