---
id: 1044
title: Brief B — Kanban Engine + Cockpit Backend/API Surface
status: archived
priority: medium
created: 2026-04-21T09:48:03.854046+00:00
updated: 2026-04-22T06:51:58.599338+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
parent:
depends_on:
- 1043
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief

Source brief: .owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md
Normative source: .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md
Depends on storage contract: parent task 1043

Scope: engine views, projections, lifecycle rules, activity/session semantics, cockpit backend/API exposure of the locked admin/history methods, MCP and cockpit adapter rewires, and engine-facing tests.

## Planner Source

Decompose from paper-integration.md §1, §4, and §5.
Respect the revised brief language: our service-side cockpit backend/API surface is in scope now, but cockpit UI/product decisions remain out of scope.
Do not create cockpit UI/operator-console tasks here; keep task 1042 separate and blocked.

## Notes

- This parent is above Brief C and below Brief A.
- The harness invariant around retries and stale end_work is locked; do not create agent-side OCC tasks that contradict it.

[[2026-04-21]]
## Planning
### Decomposition: Brief B — Kanban Engine + Cockpit Backend/API Surface
- Tasks created: 19
- Dependency layers: 10
- Phase: engine

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1065 | B-01: RED — models + errors tests | needed | #1059 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1066 | B-02: GREEN — models + errors | critical | #1065 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1067 | B-03: RED — engine init + config validation tests | needed | #1066 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1068 | B-04: GREEN — engine init + config validation | critical | #1067 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1069 | B-05: RED — list_tasks + show_task tests | needed | #1068 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1071 | B-06: GREEN — list_tasks + show_task | needed | #1069 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1070 | B-07: RED — create_task + edit_task tests | needed | #1068 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1072 | B-08: GREEN — create_task + edit_task | needed | #1070 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1073 | B-09: RED — move_task + start_work tests | needed | #1072 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1075 | B-10: GREEN — move_task + start_work | needed | #1073 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1077 | B-11: RED — end_work tests | needed | #1075 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1080 | B-12: GREEN — end_work | important | #1077 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1074 | B-13: RED — pick_tasks tests | needed | #1072 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1076 | B-14: GREEN — pick_tasks | needed | #1074 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1078 | B-15: RED — CockpitView tests | needed | #1071, #1075 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1081 | B-16: GREEN — CockpitView | needed | #1078 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1082 | B-17: RED — cockpit backend route tests | needed | #1081 | phase:engine, brief:b, scope:kanban, scope:cockpit, tdd:red |
| #1083 | B-18: GREEN — cockpit backend routes | important | #1082 | phase:engine, brief:b, scope:kanban, scope:cockpit, tdd:green |
| #1079 | B-19: orchestration skill rewrite | important | #1076 | phase:engine, brief:b, scope:kanban |

### Dependency Graph
Two parallel tracks fork from B-04 (#1068 engine init GREEN):
- Reads track: B-05 → B-06
- Writes track: B-07 → B-08 → B-09 → B-10 → B-11 → B-12
- pick_tasks fork: B-08 → B-13 → B-14 → B-19
- CockpitView: B-06 + B-10 → B-15 → B-16 → B-17 → B-18
Cross-brief: B-01 (#1065) depends on C-14 (#1059 storage.py public surface GREEN)

### Notes
- B-17/B-18 MCP adapter removed per constraint — Brief A (#1045) owns serve/mcp-kanban/
- B-19 added for w-orchestration/SKILL.md rewrite (documentation-only, depends on pick_tasks GREEN)
- CockpitView (B-15/B-16) may additionally depend on C-18 (#1063 engine activity/session wiring) at build time for list_activity/list_sessions — not added as formal dependency since tests can mock the activity store
[[2026-04-22]]
## Test-Writer Notes
- Non-implementation pass-through: parent planning/coordination task with no Acceptance Criteria section.
- Decomposition into 19 sub-tasks was already completed (B-01 through B-19, IDs #1065–#1083).
- Testable interfaces live in the sub-tasks; each RED sub-task (e.g. #1065, #1067, #1069, etc.) carries its own AC and will receive a test file scoped to that task.
- No test file created for this parent task.
- Passing through to builder.
[[2026-04-22]]
## Builder Notes
- Non-implementation pass-through task confirmed from Test-Writer Notes.
- No code changes required; parent coordination/decomposition task only.
- Files changed: none.
- Tests/lint/coverage: not applicable for this parent pass-through task.
- Passing through to review.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest: not applicable. This parent task has no Acceptance Criteria section, no task-scoped test file, and no implementation surface. Evidence: .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:85 states it is a non-implementation pass-through with no Acceptance Criteria section, and :93 states no code changes were required.
- quality-runner: not invoked because there were no task-scoped test, lint, or coverage targets to execute for this coordination-only parent task.

### Lint
- Not applicable. No source files were changed for this parent task. Evidence: .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:93.

### Coverage
- Not applicable. No implementation modules were changed for this parent task. Evidence: .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:93.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| No Acceptance Criteria section present in parent task | None | N/A | PASS - correct pass-through handling. Evidence: grep for "## Acceptance Criteria" in the task file returned no matches, and the task file states the parent has no Acceptance Criteria section at :85. |

#### Security Review
- No issues found. This task contains kanban decomposition metadata only; no code, dependency, secret, input-validation, or persistence changes are attached to this parent task.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| No TestFromAC tests exist for this parent task | None | N/A |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No task-scoped tests exist because this parent task has no executable AC. |
| Negative/error-path coverage | N/A | Child RED tasks own executable coverage. |
| Manual mutation reasoning | N/A | No implementation belongs to this parent task. |
| Test independence | N/A | No task-scoped tests exist. |
| Descriptive test names | N/A | No task-scoped tests exist. |

#### Data Safety
- No issues found. No runtime or persisted-data behavior changed in this parent task.

#### Implementation-Aware Gaps
- No untested implementation paths in this task because no implementation was delivered here. The planning section records decomposition into 19 child tasks at .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:44, and workspace search for "parent: 1044" under .owlbear/kanban/tasks returned 19 matches.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Verified the parent task's actual deliverable was decomposition: the planning section records 19 child tasks at .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:44.
- Verified downstream relevance: .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:14 lists 1044 as a dependency, and :23 cites parent task 1044 as the upstream engine contract.
- Verified this is the first review cycle for the task: grep for "## Review Evidence" in the task file returned no matches before this review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| No Acceptance Criteria section present in parent task | .owlbear/kanban/tasks/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:85 states non-implementation pass-through with no Acceptance Criteria section; :44 records 19 child tasks; workspace search for "parent: 1044" under .owlbear/kanban/tasks returned 19 matches; .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:14 and :23 confirm downstream work depends on this parent as the upstream contract. | N/A | PASS |

### Confidence: 0.96
### Verdict: PASS
[[2026-04-22]]
## Docs Gate

### Step 0
- 0a Review Evidence: PRESENT ✓
- 0b Doc-index: loaded from `.owlbear/doc-index.md` ✓

### Step 1 — Scope Classification
Changed-files set: **empty**. Builder Notes state "Files changed: none." This task is a parent coordination/decomposition task that produced 19 child sub-tasks; no source, test, or doc files were touched.

### Step 2 — Relevance-Gated Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior/API/CLI/config/package structure changed. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used; planning-only task. |
| 4 | Research doc | No | N/A | No research doc linked or produced for this parent task. |
| 5 | Diagram maintenance | No | N/A | No changed files to match against diagram `describes` globs. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs detected. |

**No docs impact.** All seven items N/A.

### Step 3 — Scratch Files
No `.owlbear/scratch/1044-*` files found. Nothing to clean.

### Step 4 — Commit
No files updated; no commit required.

### Child Tasks Created
None.
[[2026-04-22]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| No Acceptance Criteria section — parent coordination/decomposition task | Task body confirms pass-through; 19 child tasks verified via spot-check (#1065 first, #1079 middle, #1083 last) — all have parent=1044, detailed AC with brief section refs, correct tags and dependencies | PASS |

### Test Results
- pytest: 1213 passed, 59 failed, 4 skipped. All 59 failures in pre-existing modules outside task scope (cockpit read/mutation API, kanban sessions, mcp-knowledge, ideation). Zero files changed by this task — no regressions.
- ruff: 5 W292 violations in test files outside task scope. Background debt, not introduced here.

### Architect Quality: 4/5
Clean TDD red/green decomposition into 19 subtasks across 10 dependency layers. Two parallel tracks with clear fork/join. Cross-brief dependency noted. Child AC is specific with brief section references. Minor gap: no formal "done criteria" on the parent itself.

### Deduction Breakdown
- AC lines without evidence: 0 (no AC lines on parent) → 0
- Lint violations in scope: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (present, detailed) → 0
- Full-suite failures in scope: 0 → 0

### Confidence: 1.00
### Action: archive