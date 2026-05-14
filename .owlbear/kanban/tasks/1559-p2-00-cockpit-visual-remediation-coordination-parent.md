---
id: 1559
title: 'P2-00: Cockpit visual remediation coordination parent'
status: backlog
priority: critical
created: 2026-05-14T18:24:25.783282+00:00
updated: 2026-05-14T18:36:31.371686+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:coordination
  - visual-remediation
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md`.
Existing pending DR: `.owlbear/kanban/decisions/pending/1534-decision.md`.
Purpose: coordination parent for Cockpit visual remediation. This parent is for planning and lifecycle tracking, not source implementation.

## Scope
In scope: child-task tracking, dependency visibility, and DR gate visibility.
Out of scope: code changes, screenshots, source edits, and PDS asset-mode changes.

## Acceptance Criteria
AC-1: Architect records the DR #1534 response or amendment reference in this parent before moving design-dependent child implementation tasks from backlog to todo; verify by artifact inspection of the parent body or child task bodies.
AC-2: Planner links remediation child tasks under this parent and records the dependency graph in this parent body; verify by board-state inspection of parent fields and dependency fields.
AC-3: Auditor closes this parent after child remediation tasks are archived as completed, duplicate, dropped, or wontfix with references; verify by board-state audit.

Proof bundle: skip

## Evidence Expectations
Board-state inspection of parent, child, and dependency fields.
2026-05-14T18:27:39+00:00


## Planning
### Decomposition: Cockpit Visual Remediation
- Tasks created: 15 total, including this parent and 14 child tasks.
- Dependency layers: 6.
- Phase: 2.
- Source artifact: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md`.
- Decision handling: reuses pending DR `.owlbear/kanban/decisions/pending/1534-decision.md`; no duplicate DR created.

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1559 | P2-00: Cockpit visual remediation coordination parent | critical | none | phase-2, scope:cockpit, frontend, type:coordination, visual-remediation |
| 1560 | P2-01: Decide Cockpit PDS policy and redesign constraints | critical | none | phase-2, scope:cockpit, frontend, type:docs, type:design-policy, visual-remediation |
| 1561 | P2-02 RED: Guard theme-bootstrap static serving | needed | none | phase-2, scope:cockpit, frontend, type:test, bug, visual-remediation |
| 1567 | P2-03 GREEN: Serve theme-bootstrap as a static JavaScript asset | needed | 1561 | phase-2, scope:cockpit, frontend, type:build, bug, visual-remediation |
| 1562 | P2-04 RED: Specify shell and sidecar inspector behavior | needed | 1560 | phase-2, scope:cockpit, frontend, type:test, sidecar, visual-remediation |
| 1568 | P2-05 GREEN: Redesign shell and sidecar as a Cockpit inspector | needed | 1562 | phase-2, scope:cockpit, frontend, type:build, sidecar, visual-remediation |
| 1563 | P2-06 RED: Specify Cockpit overlay behavior | needed | 1560 | phase-2, scope:cockpit, frontend, type:test, overlay, visual-remediation |
| 1569 | P2-07 GREEN: Replace in-flow disclosures with Cockpit overlays | needed | 1563 | phase-2, scope:cockpit, frontend, type:build, overlay, visual-remediation |
| 1564 | P2-08 RED: Specify filter and form control behavior | needed | 1560 | phase-2, scope:cockpit, frontend, type:test, filters, forms, visual-remediation |
| 1571 | P2-09 GREEN: Recompose Cockpit filters and visible form controls | needed | 1564, 1569 | phase-2, scope:cockpit, frontend, type:build, filters, forms, visual-remediation |
| 1565 | P2-10 RED: Specify task card information density | needed | 1560 | phase-2, scope:cockpit, frontend, type:test, cards, visual-remediation |
| 1570 | P2-11 GREEN: Add compact operational metadata to task cards | needed | 1565 | phase-2, scope:cockpit, frontend, type:build, cards, visual-remediation |
| 1566 | P2-12 RED: Specify Cockpit responsive contract | needed | 1560 | phase-2, scope:cockpit, frontend, type:test, responsive, visual-remediation |
| 1572 | P2-13 GREEN: Implement the Cockpit responsive contract | needed | 1566, 1568, 1569, 1570, 1571 | phase-2, scope:cockpit, frontend, type:build, responsive, visual-remediation |
| 1573 | consolidation test: Cockpit visual remediation gates | needed | 1567, 1568, 1569, 1570, 1571, 1572 | phase-2, scope:cockpit, frontend, type:test, consolidation-test, visual-remediation |

### Dependency Graph
Layer 0: #1560 policy gate and #1561 theme-bootstrap RED can start from backlog after architect review.
Layer 1: #1567 waits on #1561. #1562, #1563, #1564, #1565, and #1566 wait on #1560.
Layer 2: #1568 waits on #1562. #1569 waits on #1563. #1570 waits on #1565.
Layer 3: #1571 waits on #1564 and #1569.
Layer 4: #1572 waits on #1566, #1568, #1569, #1570, and #1571.
Layer 5: #1573 waits on #1567, #1568, #1569, #1570, #1571, and #1572.

### Creation Commands Summary
Planner created tasks with `create_task`, parented child tasks to #1559, set explicit `depends_on` fields, and moved #1559 through #1573 to backlog. Design-dependent tasks wait on #1560 through dependency fields or transitive dependency fields. The theme-bootstrap bug lane does not wait on #1560 because it is a narrow runtime serving defect, not a design decision.


## Planner Audit Amendment — Graph Review Patch
Post-planner review compared #1559-#1573 against `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` and found four gaps: missing visual target/rubric, weak status/nav/activity coverage, missing context-menu ownership, and missing column/empty-state ownership.

Actions taken:
- Strengthened #1560 with visual target/rubric and PDS asset-mode ACs.
- Strengthened #1562/#1568 with status bar, nav rail, and activity/history row coverage.
- Strengthened #1563/#1569/#1573 with task context-menu coverage.
- Added #1574 RED and #1575 GREEN for column labels, empty states, count badges, and column-body focusability.
- Added #1575 dependency to #1572 and #1573.

Updated dependency note: #1574 depends on #1560; #1575 depends on #1574; #1572 depends on #1566, #1568, #1569, #1570, #1571, and #1575; #1573 depends on #1567, #1568, #1569, #1570, #1571, #1572, and #1575.