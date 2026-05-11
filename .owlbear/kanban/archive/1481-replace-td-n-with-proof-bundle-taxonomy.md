---
id: 1481
title: Replace td:N with proof-bundle taxonomy
status: archived
priority: needed
created: 2026-05-11T08:54:43.332169+00:00
updated: 2026-05-11T09:20:56.604029+00:00
tags:
- pipeline
- convention
- type:epic
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Brief

Replace the `(td:N)` test-depth convention with a single-axis `proof-bundle` taxonomy (skip | existing | smoke | behavioral | critical) with escalation-only modifiers (+challenge, +reader). Planner assigns during task creation; architect validates/adjusts during review. See `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md` for full design.

## Acceptance Criteria

1. `r-pipeline-protocol` defines the 5-value proof-bundle taxonomy with complete routing table
2. `w-task-decomposition` includes proof-bundle selection guide; planner writes `Proof bundle:` in task body
3. `w-arch-review` validates/adjusts planner's bundle assignment (both directions)
4. `w-tdd-red` gates test creation on proof-bundle value
5. `w-tdd-green` handles skip/existing bundles
6. `w-code-review` gates reviewer scope, code-reader, and challenger on proof-bundle + modifiers
7. `pipeline-agents.instructions.md` and agent files reference proof-bundle instead of td:N
8. Legacy `(td:N)` compatibility mapping exists in `r-pipeline-protocol`
9. No per-AC-line `(td:N)` annotation in any active skill or procedure
[[2026-05-11]]
## Planning
### Decomposition: Replace td:N with proof-bundle taxonomy
- Tasks created: 8
- Dependency layers: 3
- TDD pairing: N/A (all tasks are documentation-only Markdown changes)
- Proof bundle: skip (all tasks)

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1482 | P1-01: Define proof-bundle taxonomy in r-pipeline-protocol | critical | — | pipeline,convention,scope:skills |
| 1483 | P1-02: Add proof-bundle assignment to w-task-decomposition | needed | 1482 | pipeline,convention,scope:skills |
| 1484 | P1-03: Add proof-bundle validation to w-arch-review | needed | 1482 | pipeline,convention,scope:skills |
| 1485 | P1-04: Update w-tdd-red gating with proof-bundle | needed | 1482 | pipeline,convention,scope:skills |
| 1486 | P1-05: Update w-tdd-green handling for skip/existing bundles | needed | 1482 | pipeline,convention,scope:skills |
| 1487 | P1-06: Update w-code-review routing with proof-bundle | needed | 1482 | pipeline,convention,scope:skills |
| 1488 | P1-07: Update pipeline-agents.instructions.md and agent files | needed | 1483-1487 | pipeline,convention,scope:instructions |
| 1489 | P1-08: Final sweep — remove all remaining td:N annotations | important | 1488 | pipeline,convention |

### Dependency Graph
```mermaid
graph TD
  1482[P1-01: Define taxonomy] --> 1483[P1-02: w-task-decomposition]
  1482 --> 1484[P1-03: w-arch-review]
  1482 --> 1485[P1-04: w-tdd-red]
  1482 --> 1486[P1-05: w-tdd-green]
  1482 --> 1487[P1-06: w-code-review]
  1483 --> 1488[P1-07: Instructions/agents]
  1484 --> 1488
  1485 --> 1488
  1486 --> 1488
  1487 --> 1488
  1488 --> 1489[P1-08: Final sweep]
```

### Design Notes
- No TDD pairing: all 8 tasks are pure Markdown convention/documentation changes with no executable code
- Layer 2 (5 tasks) can execute in parallel once the foundation definition (#1482) is complete
- Critical path: 1482 → any one of 1483-1487 → 1488 → 1489 (4 layers)

[[2026-05-11]]
## Audit

### Regression Detection
No code or test changes — commit `93a4738b` adds only markdown files to `.owlbear/briefs/` and `.owlbear/kanban/`. Zero regression risk; quality-runner skipped per doc-only planning scope.

### Intent Verification
Epic purpose: plan replacement of td:N with proof-bundle taxonomy. Deliverables:
- Brief at `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md` ✓
- 8 subtasks (1482-1489) created with correct parent linkage, dependencies matching 3-layer graph, and AC covering all 9 epic AC lines ✓
- All changed files in `.owlbear/` domain — no extraneous scope ✓

### Architect Quality
AC quality score: 4/5. Nine specific, verifiable criteria each mapping to exactly one subtask. Minor gap: "complete routing table" format left to subtask-level AC (appropriate for epic granularity).

### Commit Integrity
Single atomic commit `93a4738b` — "ideation: complete Phase 2 mediation for proof-bundle taxonomy". Includes brief, panel stances, decisions, synthesis, all 8 task files, and config update. Clean attribution.

### Confidence
Start: 1.00 | Deductions: none | Final: **1.00**

Action: archive