---
id: 1045
title: Brief A — Kanban MCP Surface + Docs Sync
status: archived
priority: medium
created: 2026-04-21T09:48:09.660203+00:00
updated: 2026-04-22T23:35:12.275591+00:00
tags:
- phase:mcp
- brief:a
- scope:kanban
- docs
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief

Source brief: .owlbear/briefs/kanban-mcp-surface-v2/brief.md
Upstream engine contract: parent task 1044 and .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md

Scope: MCP tool schemas, adapter wiring, response envelopes, docs and skill sync, and MCP-facing tests after the engine/backend contract is stable.

## Planner Source

Decompose from kanban-mcp-surface-v2/brief.md, using Brief B paper-integration.md as the upstream implementation contract.
Include downstream sync work for share/skills/h-mcp-kanban/SKILL.md, serve/mcp-kanban/README.md, and any MCP-facing tests that lock the new surface.

## Notes

- This is the top layer in the implementation chain.
- Do not create cockpit UI/product tasks here.

[[2026-04-21]]
## Planning

### Task Breakdown

| ID | Title | Type | Depends On | Priority |
|---|---|---|---|---|
| #1084 | A-01: RED — MCP boundary models tests | tdd:red | #1066 (Brief B models GREEN) | needed |
| #1085 | A-02: GREEN — MCP boundary models | tdd:green | #1084 | critical |
| #1086 | A-03: RED — read tool adapter tests | tdd:red | #1085 | needed |
| #1087 | A-04: RED — mutation tool adapter tests | tdd:red | #1085 | needed |
| #1088 | A-05: RED — lifecycle tool adapter tests | tdd:red | #1085 | needed |
| #1089 | A-09: RED — guidance + error mapping tests | tdd:red | #1085 | needed |
| #1090 | A-06: GREEN — read tool adapters | tdd:green | #1086 | critical |
| #1091 | A-07: GREEN — mutation tool adapters | tdd:green | #1087, #1090 | critical |
| #1092 | A-08: GREEN — lifecycle tool adapters | tdd:green | #1088, #1091 | critical |
| #1093 | A-10: GREEN — guidance + error mapping | tdd:green | #1089, #1092 | needed |
| #1094 | A-11: docs sync — h-mcp-kanban skill + README | docs | #1093 | needed |

### Dependency Graph

```
#1066 (Brief B models GREEN)
  └─ #1084 (A-01 RED models)
       └─ #1085 (A-02 GREEN models)
            ├─ #1086 (A-03 RED reads)
            │    └─ #1090 (A-06 GREEN reads)
            │         └─ #1091 (A-07 GREEN mutations)
            │              └─ #1092 (A-08 GREEN lifecycle)
            │                   └─ #1093 (A-10 GREEN guidance)
            │                        └─ #1094 (A-11 docs sync)
            ├─ #1087 (A-04 RED mutations) ──→ #1091
            ├─ #1088 (A-05 RED lifecycle) ──→ #1092
            └─ #1089 (A-09 RED guidance) ──→ #1093
```

### Layers
1. **L1** (#1084): MCP boundary models RED — cross-brief gate on Brief B #1066
2. **L2** (#1085): MCP boundary models GREEN — gate for all tool tests
3. **L3** (#1086, #1087, #1088, #1089): 4 RED test tasks — parallelizable
4. **L4** (#1090 → #1091 → #1092 → #1093): 4 GREEN impl tasks — serialized on server.py
5. **L5** (#1094): docs sync — last

### Design Notes
- Cross-brief dependency: #1084 → #1066 (Brief B models GREEN). MCP response envelopes reuse engine projection types (TaskSummary, TaskFull, etc.) so engine models must be implemented and importable before MCP model tests can be written.
- Adapter is a mechanical translator per paper-integration.md §1 ("1:1 signature passthrough", "Adapter is mechanical (O6)"). All business logic in engine via AgentView.
- All adapter tests mock AgentView — no engine integration in Brief A scope.
- GREEN impl tasks serialize on server.py to avoid merge conflicts: reads → mutations → lifecycle → guidance.
- AC13 (edit_task rejects status param) enforced at adapter schema level, not engine.
[[2026-04-22]]
## Test-Writer Notes
- Non-implementation task (tagged `brief:a`) — no tests applicable.
- Task body contains only architect planning: brief scope, subtask breakdown, and dependency graph. No Acceptance Criteria section, no testable Python interfaces.
- All test-writing work delegated to subtasks: #1084 (RED models), #1086 (RED reads), #1087 (RED mutations), #1088 (RED lifecycle), #1089 (RED guidance).
- #1084 is already in-progress with 51 failing tests written.
- Passing through to builder.
[[2026-04-22]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Scope is planning/decomposition only; implementation is delegated to child tasks (#1085, #1090-#1094 and related RED prerequisites).
- Passing through to review.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest: N/A. The task body is a planning/decomposition artifact with no executable Acceptance Criteria section and no task-scoped implementation to run.

### Lint: N/A
- No task-scoped source or test module is attached to #1045 itself; downstream executable work is delegated to child tasks.

### Coverage: N/A
- No reviewable implementation surface exists on this parent task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A. #1045 has no `## Acceptance Criteria` section and no `TestFromAC_*` test file. The test-writer correctly passed executable coverage to child tasks #1084, #1086, #1087, #1088, and #1089.

#### Security Review
- No code or dependency changes are in scope on this parent planning task.

#### Test Integrity
- N/A. No task-scoped `TestFromAC_*` classes exist for #1045.

#### Test Quality
| Dimension | Rating | Evidence |
|---------|--------|----------|
| Assertion specificity | N/A | No task-scoped executable tests exist for #1045. |
| Negative/error-path coverage | N/A | Executable coverage belongs to child RED tasks, not this parent planning task. |
| Manual mutation reasoning | N/A | No implementation surface exists on #1045. |
| Test independence | N/A | No task-scoped tests exist. |
| Descriptive test names | N/A | No task-scoped tests exist. |

#### Data Safety
- No implementation diff to assess on this parent task.

#### Implementation-Aware Gaps
- FAIL: the planning artifact's task graph is internally inconsistent. `.owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md` sets `depends_on: 1044` (lines 13-14) and names `parent task 1044` as the upstream engine contract (line 25), but `show_task(1044)` returned `Task '1044' not found in .owlbear/kanban/tasks` and a repository file search for `.owlbear/kanban/**/*1044*.md` returned no task file.
- FAIL: the same planning artifact then uses a different upstream gate, `#1066`, throughout the actual decomposition: line 46 (`#1084 ... Depends On #1066`), line 61 (`#1066 (Brief B models GREEN)`), line 76 (`cross-brief gate on Brief B #1066`), and line 83 (`#1084 -> #1066`). The spawned child task `.owlbear/kanban/tasks/1084-a-01-red-mcp-boundary-models-tests.md` also depends on `1066` at lines 14-15 and explains that cross-brief dependency at line 29.
- PASS: aside from the broken upstream reference, the decomposition coverage itself is coherent: tasks #1084-#1094 cover models, reads, mutations, lifecycle, guidance/error mapping, and docs sync.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The concrete child task graph is otherwise well-formed: #1084 exists and is in-progress, while #1085-#1094 exist in todo and align with Brief A sections 5-7.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| No explicit AC section in #1045 task body | `.owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md` contains `## Brief`, `## Planner Source`, `## Notes`, and `## Planning`, but no `## Acceptance Criteria` block. | N/A | INFO |
| Upstream dependency reference is valid and internally consistent | #1045 lines 13-14 and 25 reference `1044`; no `1044` task file exists; `show_task(1044)` failed; #1045 lines 46, 61, 76, 83 and #1084 lines 14-15, 29 use `1066` instead. | N/A | FAIL |
| Brief A scope is decomposed into concrete downstream tasks | #1045 lines 44-84 create #1084-#1094 covering the required MCP surface and docs sync. | N/A | PASS |

### Confidence: 0.82
### Verdict: FAIL
### Action
- Reject to `backlog`. This is a planning/task-graph defect, not an implementation defect: the parent task's own dependency metadata and upstream contract reference need architect/planner cleanup before the parent can progress.
[[2026-04-22]]
## Architecture Review

### Context
Reviewer returned this task to backlog (confidence 0.82) citing two FAIL findings:
1. `depends_on: 1044` references a task that `show_task(1044)` cannot find
2. Body references "parent task 1044" but decomposition uses #1066

**Both are false positives.** Task #1044 ("Brief B — Kanban Engine + Cockpit Backend/API Surface") exists in the archive (status: archived, confirmed via `list_tasks(archived=true)`). The `show_task` tool only searches active tasks, which caused the reviewer's lookup to fail. The dependency was valid and already satisfied (archived = done).

The decomposition's use of #1066 as the cross-brief gate is correct — it's the specific subtask-level dependency (B-02: GREEN models) that Brief A's first subtask (#1084) needs. This is a different granularity than the brief-level #1044 dependency.

### Fixes Applied
- **Added `docs` pass-through tag** — task produces no testable Python code; `docs` ensures test-writer/builder pass through cleanly per pipeline protocol
- **Cleared `depends_on: [1044]` → `[]`** — dependency was satisfied (archived/done) and caused tooling confusion; historical link preserved in body text

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Planning/decomposition container for Brief A |
| Interface clarity | PASS | Planning section defines 11 subtasks with clear scope and deps |
| Dependency correctness | PASS | #1044 was satisfied (archived); cross-brief gate #1066 correct |
| Module layering | N/A | No code |
| TDD compliance | N/A | No code; subtasks carry TDD pairs |
| KISS/YAGNI | PASS | Minimal planning structure |
| Premise challenge | PASS | Brief A needs a parent planning task |
| Pattern consistency | PASS | Standard brief parent pattern |
| Security surface | N/A | No code |
| Single domain | PASS | MCP kanban domain only |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in tool allowlist
- Architect response: N/A (fallback)

### Verdict: APPROVE (REFINE path — fixes applied, then approved)
### Action Taken
Corrected reviewer false positive re #1044 (exists in archive, not missing). Added `docs` pass-through tag. Cleared stale depends_on. Advancing to todo.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL was a planning metadata defect (broken `depends_on: 1044` reference), not missing tests.
- Architect fixed: cleared stale `depends_on`, added `docs` tag, confirmed #1044 exists in archive.
- No testable Python interfaces on this parent planning task. All executable test work delegated to child RED tasks (#1084, #1086, #1087, #1088, #1089).
- Pass-through to builder per Step 1b (non-test failure) + Step 1a (`docs` tag).
[[2026-04-22]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Files changed: none.
- Tests: N/A (parent planning/docs pass-through; executable coverage is delegated to child implementation tasks).
- Coverage: N/A.
- Lint: N/A.
- Evidence summary: task body `## Test-Writer Notes` explicitly marks this as a non-implementation pass-through task with no testable Python interfaces.
- Fixes applied: none.

### Reflection
- problems_faced: none.
- workarounds_applied: followed Step 0a non-implementation pass-through from w-tdd-green.
- patterns_discovered: parent planning tasks with `docs`/non-impl notes should be closed without code edits.
- quality_gaps: none on this task; quality checks are owned by child implementation tasks.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest: N/A on parent task 1045. This task has no Acceptance Criteria block and no task-scoped implementation or test module. Independent verification instead confirmed that delegated executable work exists under child task 1084: .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:91 and :200, .owlbear/kanban/tasks/1084-a-01-red-mcp-boundary-models-tests.md:42-45, and serve/mcp-kanban/tests/test_mcp_models_1084.py:1-13.

### Lint: N/A
- No task-scoped Python source or test path is attached to the parent planning task. The builder also recorded files changed: none at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:205.

### Coverage: N/A
- No touched runtime module exists on this parent planning artifact.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A. Task 1045 has no Acceptance Criteria section and no TestFromAC classes. The task body explicitly marks it as planning-only and delegates executable coverage to child tasks 1084, 1086, 1087, 1088, and 1089 at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:91 and :200.

#### Security Review
- No code or dependency changes are in scope. The current task state is metadata and planning only: docs tag present and depends_on cleared at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:12-14; builder recorded files changed none at :205.

#### Test Integrity
- N/A. No task-scoped TestFromAC classes exist for 1045.

#### Test Quality
| Dimension | Rating | Evidence |
|---------|--------|----------|
| Assertion specificity | N/A | No task-scoped executable tests exist on the parent planning task. |
| Negative or error-path coverage | N/A | Executable coverage belongs to child RED tasks, not this parent planning task. |
| Manual mutation reasoning | N/A | No implementation surface exists on 1045 itself. |
| Test independence | N/A | No task-scoped tests exist on the parent task. |
| Descriptive test names | N/A | No task-scoped tests exist on the parent task. |

#### Data Safety
- No implementation diff or persisted data path was changed on this review target.

#### Implementation-Aware Gaps
- No defect remains. The prior failure reason was incorrect: archived task 1044 exists in .owlbear/kanban/archive/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:2-4 and is also returned by list_tasks with archived=true. The historical upstream reference at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:25 is therefore valid.
- The apparent 1044 versus 1066 split is intentional, not inconsistent. Task 1045 preserves the brief-level upstream contract at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:25 while the decomposition names the specific child gate 1066 at :83 and .owlbear/kanban/tasks/1084-a-01-red-mcp-boundary-models-tests.md:29.
- The parent decomposition remains complete for Brief A scope through child tasks 1084-1094 at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:44-84.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- show_task does not surface archived tasks; archived dependency validation should use list_tasks with archived=true before flagging a missing upstream task.
- Child task 1084 is active and bound to the specific cross-brief gate 1066, which matches the planning graph.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| No explicit Acceptance Criteria section on parent planning task | .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:91 states there is no Acceptance Criteria section and no testable Python interfaces. | N/A | INFO |
| Parent task is clearly marked as non-implementation pass-through | docs tag at .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:12, cleared depends_on at :14, and builder files changed none at :205. | N/A | PASS |
| Brief-level upstream reference is valid | Archived task file 1044 exists at .owlbear/kanban/archive/1044-brief-b-kanban-engine-cockpit-backend-api-surface.md:2-4 and list_tasks with archived=true returns task 1044 archived. | N/A | PASS |
| Cross-brief gate for child execution is internally consistent | .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:83 and .owlbear/kanban/tasks/1084-a-01-red-mcp-boundary-models-tests.md:29 both name 1066 as the specific model gate for child task 1084. | N/A | PASS |
| Brief A scope is decomposed into concrete downstream work | .owlbear/kanban/tasks/1045-brief-a-kanban-mcp-surface-docs-sync.md:44-84 lays out tasks 1084-1094, and .owlbear/kanban/tasks/1084-a-01-red-mcp-boundary-models-tests.md:42 plus serve/mcp-kanban/tests/test_mcp_models_1084.py:1-13 confirm a real delegated test artifact exists. | N/A | PASS |

### Deductions
- 0.04: No task-scoped runtime surface exists, so confidence comes from metadata and downstream artifact verification rather than direct test execution on the parent task.

### Confidence: 0.96
### Verdict: PASS
### Action
- Advance to docs. No reviewable implementation or test-quality defect remains on the parent task after the architect's metadata correction.

### Reflection
- problems_faced: prior review treated an archived upstream task as missing because show_task only sees active tasks.
- workarounds_applied: validated the archived dependency with list_tasks archived=true and archive-file evidence.
- patterns_discovered: parent planning tasks tagged docs can legitimately carry N/A test, lint, and coverage results when executable work is delegated to child tasks, but the delegated task and test artifacts still need to be verified.
[[2026-04-22]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder: "Files changed: none." No behavior, API, CLI, config, or package-structure change. No IN-scope doc references the changed area. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns or sources used. Pure planning/decomposition task. |
| 4 | Research doc | No | N/A | No research phase for this task. No `.owlbear/research/` file produced. |
| 5 | Diagram maintenance (describes match) | No | N/A | Changed-files set is empty (builder: "Files changed: none"). Kanban task file metadata updates are pipeline ops data, not source changes that `kanban.excalidraw` or `project-overview.excalidraw` depict. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1045-*.md` | OUT (kanban ops metadata) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1045-*` scratch files found)
[[2026-04-22]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Brief A scope decomposed into concrete downstream tasks | Task body lines 44-84: 11 subtasks (#1084-#1094) covering models, reads, mutations, lifecycle, guidance, docs | PASS |
| Child tasks exist and are properly formed | All 11 child tasks confirmed present in .owlbear/kanban/tasks/ with correct titles matching decomposition table | PASS |
| Cross-brief dependency gate is consistent | #1066 named as gate in decomposition (line 83) and in child #1084 (line 29); #1044 archived and valid as brief-level reference | PASS |
| Non-implementation pass-through correctly tagged | `docs` tag present; builder confirmed "Files changed: none"; test-writer delegated to child RED tasks | PASS |

### Test Results
- pytest: 1262 passed, 117 failed, 4 skipped — 0 failures in task scope (no files changed by #1045). Failures are from in-progress child work (51 MCP model imports, 24 session contract changes, etc.)
- ruff: 5 W292 violations in pre-existing test files — not in task scope

### Architect Quality: 4/5
Thorough decomposition with clear dependency layering and serialization strategy. Minor metadata sloppiness (stale `depends_on: 1044` referencing archived task) caused one rework cycle but was corrected. Planning substance is solid.

### Deduction Breakdown
- -0.02: No formal AC section — verification is indirect (metadata + downstream artifact existence only), inherent to planning-container task type
- No deduction for test failures (0 files changed, none in scope)
- No deduction for lint (pre-existing W292, not in scope)
- No deduction for reviewer evidence (present, detailed, PASS at 0.96)

### Confidence: 0.98
### Action: archive