---
id: 1437
title: Simplify kanban topology for deployment readiness
status: archived
priority: medium
created: 2026-05-08T19:26:13.098440+00:00
updated: 2026-05-09T00:51:41.548916+00:00
tags:
- deployment-readiness
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Deployment readiness audit found that the kanban engine, MCP server, Cockpit bridge, setup seed, and agent guidance expose too much board topology as editable config. The approved direction is to remove configurable board topology, make dispatch/read behavior explicit, and split cleanup/DR mutation into named operations.

## Approved Direction

- Remove configurable statuses, priorities, paths, agent routing, archival reasons, activity behavior, and dispatch policy.
- Prefer no next_id state file: allocate IDs by scanning active + archived task filename prefixes under a create lock.
- Make pick_tasks read-only: compute expired-claim eligibility but do not sweep or resolve DRs.
- Keep start_work as the atomic writer that clears/reclaims expired claims.
- Add an explicit resolve_drs MCP tool and remove DR resolution side effects from pick_tasks.
- Keep sweep/cleanup user-triggered via Cockpit maintenance.
- Centralize destination validation for all status-changing paths.
- Correct MCP annotations/descriptions and normalize MCP errors.
- Fix list filter semantics.
- Hard-code activity logging on and emit complete mutation events, including task creation.
- Wire create_dr end-to-end for pipeline agents and guidance.

## Planning Constraints

Needs decomposition: create implementation child tasks for the full remediation, with every child task placed in backlog, not todo. Each child task must have actionable, clear, measurable acceptance criteria. Split by domain and responsibility. Use explicit dependencies. Do not create placeholder tasks.

## Acceptance Criteria

- [ ] The planner creates an implementation task graph covering engine, MCP, Cockpit, setup/seed, agent guidance, docs, migration/cleanup, and verification probes.
- [ ] Every child task is created in backlog status.
- [ ] Each child task has clear, measurable AC suitable for architect review.
- [ ] Dependencies between slices are explicit.
- [ ] The plan avoids running the test suite as deployment proof; verification tasks use isolated scratch-board probes and contract inspection.

[[2026-05-08]]

## Planning
### Decomposition: Simplify kanban topology for deployment readiness
- Tasks created by this planner pass: 20 (#1438 through #1457)
- Dependency layers: 10
- Phase: 4
- Status policy: child tasks were moved to backlog; no test suite was run.
- Concurrency note: parent #1437 was observed in todo during final inspection due to a separate board update; this planner did not advance the parent.

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1438 | P4-01: Probe fixed kanban topology contract | needed | none | phase-4, scope:kanban, type:test |
| 1439 | P4-02: Collapse kanban engine topology into product constants | critical | 1438 | phase-4, scope:kanban, type:refactor |
| 1440 | P4-03: Probe setup seed without config.yml writes | needed | none | phase-4, scope:setup, type:test |
| 1441 | P4-04: Remove config.yml from setup seed and board initialization | needed | 1440, 1439 | phase-4, scope:setup, type:refactor |
| 1442 | P4-05: Probe scan-based task ID allocation and activity events | needed | none | phase-4, scope:kanban, type:test |
| 1443 | P4-06: Replace next_id config allocation and hard-code activity logging | needed | 1442, 1439 | phase-4, scope:kanban, type:refactor |
| 1444 | P4-07: Probe read-only dispatch and atomic claim reclamation | needed | none | phase-4, scope:kanban, type:test |
| 1445 | P4-08: Make pick_tasks read-only and keep start_work as claim writer | critical | 1444, 1439, 1443 | phase-4, scope:kanban, type:refactor |
| 1446 | P4-09: Probe explicit decision resolver behavior | needed | none | phase-4, scope:mcp-kanban, type:test |
| 1447 | P4-10: Add retry-safe resolve_drs MCP operation | critical | 1446, 1445 | phase-4, scope:mcp-kanban, type:build |
| 1448 | P4-11: Probe maintenance cleanup semantics | needed | none | phase-4, scope:maintenance, type:test |
| 1449 | P4-12: Add user-triggered cleanup for expired claims and archived moves | needed | 1448, 1445 | phase-4, scope:kanban, type:build |
| 1450 | P4-13: Probe MCP list filters, annotations, and error envelopes | needed | none | phase-4, scope:mcp-kanban, type:test |
| 1451 | P4-14: Normalize MCP filters, annotations, and errors | needed | 1450, 1445, 1447 | phase-4, scope:mcp-kanban, type:build |
| 1452 | P4-15: Probe create_dr guidance and pipeline integration | needed | none | phase-4, scope:agents, type:test |
| 1453 | P4-16: Wire create_dr end to end for agents and guidance | needed | 1452, 1447, 1451 | phase-4, scope:agents, type:build |
| 1454 | P4-17: Probe documentation and agent guidance contract | needed | none | phase-4, scope:docs, type:test |
| 1455 | P4-18: Update deployment docs and agent guidance | needed | 1454, 1439, 1441, 1443, 1445, 1447, 1449, 1451, 1453, 1457 | phase-4, scope:docs, type:docs |
| 1457 | P4-19: Expose maintenance cleanup through Cockpit | needed | 1448, 1449 | phase-4, scope:cockpit, type:build |
| 1456 | P4-20: consolidation test: fixed-topology deployment readiness | important | 1439, 1441, 1443, 1445, 1447, 1449, 1451, 1453, 1455, 1457 | phase-4, consolidation-test, type:test |

### Dependency Graph
Root probes: 1438, 1440, 1442, 1444, 1446, 1448, 1450, 1452, 1454.
Implementation pairs: 1438 before 1439; 1440 before 1441; 1442 before 1443; 1444 before 1445; 1446 before 1447; 1448 before 1449 and 1457; 1450 before 1451; 1452 before 1453; 1454 before 1455.
Integration gates: 1455 depends on completed implementation slices; 1456 depends on implementation and docs slices.

### Creation Commands
Created each child with create_task(title), then applied edit_task(parent=1437, priority, tags, body, dependencies) and move_task(status=backlog).

[[2026-05-08]]
## Architecture Review

### Verdict: APPROVE

Planner completed successfully — `## Planning` section present with 20 child tasks (#1438–#1457).

### AC Verification
| AC | Assessment | Evidence |
|----|-----------|----------|
| Task graph covers all domains | PASS | 9 domain slices: engine, MCP, Cockpit, setup/seed, agents, docs, cleanup, probes, consolidation |
| Every child in backlog | PASS | Planner moved all to backlog; #1438 already advanced to todo by separate architect pass (expected) |
| Clear measurable AC | PASS | Spot-checked #1438 (4 AC), #1445 (5 AC), #1453 (5 AC), #1456 (7 AC) — all specific and testable |
| Explicit dependencies | PASS | Probe→implementation pairs, integration gates (#1455, #1456) gated on completed slices |
| No test suite as proof | PASS | All tasks use scratch-board probes and contract inspection, explicitly exclude pytest/vitest |

### Notes
- Decomposition follows TDD probe-first pattern: 9 root probes run independently, each gates its paired implementation task.
- Consolidation test #1456 depends on all implementation + docs slices — correct final gate.
- #1438 already architect-reviewed and refined (expanded topology surface to 13 constant categories).
[[2026-05-08]]
## Test-Writer Notes
- Non-impl pass-through: all 5 AC lines describe kanban board-state deliverables (task graph creation, backlog status, AC quality, explicit dependencies, policy constraint).
- No Python source files, modules, classes, or functions referenced in any AC line.
- Implementation intent keywords absent from AC.
- Planning section confirms planner completed the task graph (20 child tasks, #1438–#1457); Architect reviewed and approved.
- Passing through to builder with no tests needed.
[[2026-05-08]]
## Builder Notes
- Non-implementation task confirmed from `## Test-Writer Notes`.
- No code changes required; no tests or lint runs required for this pass-through.
- Scope is kanban board-state planning/structure deliverables only (already produced and architect-approved).
- Passing through to review.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner: skipped. This is a td:0 planning / board-state task with no task-owned source files, test files, or runtime artifact to execute. Review evidence comes from the parent task artifact and the 20 child task records under `.owlbear/kanban/tasks/`.

### Lint: skipped
- No code or test files were changed by this task. Lint evidence is not applicable to a planning-only deliverable.

### Coverage: skipped
- No touched modules. Coverage is not applicable to this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Task graph covers engine, MCP, Cockpit, setup/seed, agent guidance, docs, migration/cleanup, and verification probes | N/A (td:0 artifact review) | Yes — missing or mis-scoped child tasks would be visible in the parent task list and child task files | COVERED |
| Every child task is created in backlog status | N/A (td:0 artifact review) | Partially — current child statuses plus the parent planning record show backlog placement intent and later downstream advancement; historical creation-time proof is slightly lower confidence because activity-log evidence is unavailable | COVERED |
| Each child task has clear, measurable AC suitable for architect review | N/A (td:0 artifact review) | Yes — missing or vague AC would be visible in child task bodies | COVERED |
| Dependencies between slices are explicit | N/A (td:0 artifact review) | Yes — missing dependencies would be visible in `depends_on` frontmatter and the parent dependency graph | COVERED |
| Plan avoids test-suite proof; verification tasks use scratch-board probes and contract inspection | N/A (td:0 artifact review) | Yes — forbidden pytest/vitest proof language or missing probe wording would be visible in the child AC text | COVERED |

#### Security Review
- No security issues found. Scope is kanban task-graph creation only; no executable surface, dependency change, secret exposure, or input-handling path was added by this task.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| N/A | No tests were created or modified by this planning task | N/A |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No tests in scope |
| Negative/error-path coverage | N/A | No tests in scope |
| Manual mutation reasoning | N/A | No tests in scope |
| Test independence | N/A | No tests in scope |
| Descriptive test names | N/A | No tests in scope |

#### Data Safety
- No data-safety issues found. The deliverable is the child-task graph itself, and the resulting task artifacts are structurally coherent.

#### Implementation-Aware Gaps
- No untested implementation paths apply. The deliverable is a planning graph, not source behavior.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Current child statuses already reflect downstream progress (`todo`, `docs`, `in-progress`, and `backlog` mixed across the graph). That is consistent with the planner having created backlog tasks which later advanced, but the review cannot reconstruct every creation-time transition from `.owlbear/kanban/activity.jsonl`; confidence is reduced slightly rather than blocked.
- Representative direct reads across domains confirm measurable AC shape: kanban probe `[1438]`, setup `[1441]`, MCP `[1447]`, agent guidance `[1453]`, Cockpit `[1457]`, and consolidation `[1456]` all use concrete observable outcomes rather than placeholders.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| The planner creates an implementation task graph covering engine, MCP, Cockpit, setup/seed, agent guidance, docs, migration/cleanup, and verification probes. | Parent task `.owlbear/kanban/tasks/1437-simplify-kanban-topology-for-deployment-readiness.md` lists 20 children and the domain slices. Direct child reads confirm setup (`#1441`), MCP (`#1447`), agents (`#1453`), Cockpit (`#1457`), and consolidation / verification (`#1456`). Grep on `parent: 1437` returns 20 child task files. | N/A | PASS |
| Every child task is created in backlog status. | Parent planning record states `move_task(status=backlog)` for each child. Live child frontmatter shows many tasks still in `backlog` (`#1439`, `#1441`, `#1447`, `#1453`, `#1456`, `#1457`) while several probe tasks have already advanced (`#1438` `todo`, `#1440` `docs`, `#1454` `in-progress`), which is consistent with later workflow movement. | N/A | PASS |
| Each child task has clear, measurable AC suitable for architect review. | Grep confirms `## Acceptance Criteria` exists in all 20 child task files. Direct reads of `#1438`, `#1441`, `#1447`, `#1453`, `#1456`, and `#1457` show bounded scope plus enumerated observable outcomes. | N/A | PASS |
| Dependencies between slices are explicit. | Child `depends_on` frontmatter is explicit: `#1439 -> #1438`, `#1441 -> #1440 + #1439`, `#1453 -> #1452 + #1447 + #1451`, `#1456 -> #1439 + #1441 + #1443 + #1445 + #1447 + #1449 + #1451 + #1453 + #1455 + #1457`. Parent dependency graph matches those edges. | N/A | PASS |
| The plan avoids running the test suite as deployment proof; verification tasks use isolated scratch-board probes and contract inspection. | Parent AC and planning note prohibit suite-as-proof. Representative child ACs explicitly require scratch-board probes / contract inspection and forbid pytest/vitest proof (`#1438`, `#1441`, `#1450`, `#1452`, `#1456`, `#1457`). | N/A | PASS |

### Confidence: 0.92
### Verdict: PASS
### Action
- Advance to `docs`.

[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Planning task — no behavior, API, CLI, config, or package structure changed |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | No external patterns used; pure board decomposition |
| 4 | Research doc | No | N/A | No research phase; no `.owlbear/research/` file referenced in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No IN-scope files changed; no describes-match possible |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1437-*.md` (+ 20 children) | OUT | Board operational data — not IN-scope documentation |

No docs impact. Deliverable is the child task graph (#1438–#1457) only.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files for task #1437 existed)
[[2026-05-09]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Task graph covers engine, MCP, Cockpit, setup/seed, agent guidance, docs, migration/cleanup, and verification probes | Grep `parent: 1437` returns 18 active task files + 2 archived (#1440, #1444). Total 20 children across 9 domain slices: engine (#1438/#1439), setup (#1440/#1441), ID allocation (#1442/#1443), dispatch (#1444/#1445), decisions (#1446/#1447), maintenance (#1448/#1449), MCP (#1450/#1451), agents (#1452/#1453), docs (#1454/#1455), Cockpit (#1457), consolidation (#1456). | PASS |
| Every child task created in backlog status | Parent planning record states `move_task(status=backlog)` for each child. Current states: many still in backlog (#1439, #1441, #1447, #1453, #1456, #1457), others advanced through pipeline (#1440 archived, #1444 archived, #1438 todo+, #1448 in-progress+, #1450 in-progress+). Consistent with backlog creation followed by pipeline advancement. | PASS |
| Each child has clear, measurable AC | Spot-checked #1445 (5 AC lines, specific function/method contracts), #1456 (7 AC lines, concrete walkthrough deliverables), #1453 (5 AC, end-to-end wire checks). All specific and testable. Consistent with reviewer's spot-check of #1438, #1441, #1447. | PASS |
| Dependencies between slices are explicit | Verified depends_on frontmatter: #1445→[1444,1439,1443], #1456→[1439,1441,1443,1445,1447,1449,1451,1453,1455,1457], #1441→[1440,1439]. Parent dependency graph matches child frontmatter edges. | PASS |
| Plan avoids test-suite proof; uses scratch-board probes and contract inspection | Child ACs (#1445 AC5, #1456 AC7) explicitly prohibit pytest/vitest as functional proof. Verification tasks use scratch-board walkthroughs and contract inspection artifacts. | PASS |

### Test Results
- pytest: 460 failures — all from active child task development (TDD RED phase tests for #1448, #1450; in-progress engine/MCP refactoring from #1439 children). Task #1437 made zero code changes. Recent pre-child-refactoring runs (terminal history) show clean suite. Consolidation test #1456 exists as final gate.
- ruff: 12 violations — all in serve/tools/ and serve/knowledge/ (pre-existing debt; copilot_auth.py, test_root.py, test_test_root.py). None from #1437.

### Architect Quality: 4/5
AC is clear and measurable for a planning task. All 5 lines describe concrete, verifiable deliverables. Minor gap: AC2 "created in backlog status" is only verifiable via planner self-report since activity log evidence is unavailable for historical creation-time state. Reasonable for a planning task.

### Deduction Breakdown
- Starting: 1.00
- AC2 historical creation-time verification limited to planner self-report (activity log unavailable): -.02
- Lint violations: 0 (pre-existing, not from this task)
- Full-suite failures: 0 (task has no code scope; failures from child task development)
- AC quality ≤ 3: No (4/5)
- Missing reviewer evidence: No (detailed, 0.92 PASS)

### Confidence: 0.98
### Action: archive