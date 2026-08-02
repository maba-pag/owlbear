---
id: 1237
title: 'Architect calibration: dependency-graph direction and infeasible test gates
  in frontend refactor AC'
status: archived
priority: medium
created: 2026-05-01T02:10:20.377775+00:00
updated: 2026-05-01T08:35:17.619451+00:00
tags:
- calibration
- architect
- ac-quality
- frontend
- quality
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Spawned from task #1225 (KanbanBoard split into Card/Column/Board components). AC quality scored 3/5. Two defects required full architect re-review and a second pipeline cycle.

## Defect 1 — Inverted dependency-graph direction

AC Line 3 specified that `KanbanBoard.tsx` should import `Card` directly. The correct dependency chain is `KanbanBoard → Column → Card` (Board owns Columns; Columns own Cards). The AC inverted this, making `KanbanBoard → Card` a direct import — which bypasses Column and collapses the intended layering.

The implementation was architecturally correct; the AC was wrong. The reviewer correctly failed the task, triggering an avoidable cycle.

## Defect 2 — Infeasible must-pass gate (pre-existing red suite)

AC Line 6 named `test_cockpit_react_compiler_1015.py` as a must-pass gate. That suite had 4 pre-existing failures (vite/package config + E2E) that predate task #1225. Naming an already-red suite as a hard gate made the gate infeasible on a green implementation, causing reviewer FAIL.

## Acceptance Criteria

1. Architect produces a written calibration note (appended to this task body or as a `.owlbear/decisions/` entry) covering:
   a. **Dependency-graph direction rule:** For frontend component AC, always trace the `parent → child` ownership chain from live code before writing import-shape constraints. AC must name the correct importer and importee based on the actual component hierarchy.
   b. **Suite health pre-check rule:** Before naming a durable test suite as a must-pass gate in AC, run or inspect the suite to confirm it is currently green. If the suite has pre-existing failures unrelated to the task, either (a) exclude the failing tests from the gate with an explicit note, or (b) name a scoped subset of the suite that is known-green.
2. Calibration note references task #1225 as the triggering case.
3. Follow-up kanban tasks are created if either rule requires a systemic fix (e.g., a checklist update to the architect skill or brief template).


## AC Test-Depth Annotations

- AC1: Calibration note with two sub-rules (td:0)
- AC2: Reference task #1225 (td:0)
- AC3: Create follow-up tasks if systemic fix needed (td:0)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One calibration covering two related defects from #1225 |
| Interface clarity | PASS | Deliverable location specified (task body or `.owlbear/decisions/`) |
| Dependency correctness | PASS | No deps needed; #1225 is context only |
| Module layering | N/A | Non-code deliverable |
| TDD compliance | N/A | Non-implementation task; `quality` pass-through tag added |
| KISS/YAGNI | PASS | Minimal scope: write note, create follow-ups if warranted |
| Premise challenge | PASS | Two real defects caused avoidable pipeline cycles; calibration is the correct response |
| Pattern consistency | PASS | Calibration notes are an established pattern |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Architect process quality |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Builder Guidance
Both defects represent genuine systemic gaps in `w-arch-review`:
1. No explicit step to trace live import chains before writing component-hierarchy AC (Defect 1)
2. No explicit step to verify named test suites are green before gating on them (Defect 2)

The builder should: (a) write the calibration note per AC1–AC2, and (b) create follow-up task(s) to update the `w-arch-review` skill with these two checks (AC3). Suggested location for follow-up: `backlog` with tag `agent`.

### Verdict: APPROVE
### Action Taken: Added `quality` pass-through tag, annotated AC with td:0, approved to todo
[[2026-05-01]]
Architecture review complete. Non-implementation calibration task — all AC lines td:0. Added `quality` pass-through tag. Both defects trace to genuine gaps in w-arch-review: (1) no live import-chain check before writing component AC, (2) no suite health pre-check before naming must-pass gates. Builder guidance included for follow-up task creation.
[[2026-05-01]]
## Test-Writer Notes

Non-implementation pass-through.

**Evidence:**
- All 3 AC lines annotated `td:0` by architect
- Architecture Review section explicitly states `Test-writer: SKIP`
- Task tagged `quality` (pass-through tag)
- Deliverable is a calibration note + follow-up task creation — no Python source, no testable interfaces

**No test file created.** Builder proceeds directly.
[[2026-05-01]]

## Calibration Note (Architect)

Triggering case: task #1225.

1. Dependency-graph direction rule
- For frontend component AC, derive import-shape constraints from the live ownership chain (`parent -> child`) before writing AC.
- AC must name the correct importer/importee based on current hierarchy (example from #1225: `KanbanBoard -> Column -> Card`; avoid collapsing to `KanbanBoard -> Card` unless the live hierarchy actually changed).

2. Suite health pre-check rule
- Before naming any durable suite as a must-pass gate, verify that suite is currently green (run or inspect latest reliable evidence).
- If the suite has pre-existing unrelated failures, AC must either:
  - scope the gate to a known-green subset, or
  - explicitly exclude known failing tests with rationale.

Systemic follow-up created per AC3: #1258 (backlog) to update `w-arch-review` with both checks and checklist wording.

[[2026-05-01]]
## Builder Notes
- Non-implementation pass-through (`td:0` ACs; no code/test edits required).
- Calibration note appended to task body covering:
  - dependency-graph direction rule (`parent -> child` live ownership check), and
  - suite-health pre-check rule for must-pass durable gates.
- Triggering case explicitly referenced: #1225.
- Follow-up created for systemic fix: #1258 (backlog) to update `w-arch-review` checklist/workflow with both checks.
- Tests: not applicable for this task type.
- Coverage: not applicable for this task type.
- ruff: not applicable for this task type.
[[2026-05-01]]
## Review Evidence
### Test Results
- Quality-runner td:0 evidence pass: tests not applicable for this non-implementation calibration task.
- Quality-runner report: 0 passed, 0 failed, 0 skipped; no task-owned test file exists for #1237.

### Lint
- Quality-runner: not applicable. No task-scoped source or test files were modified for this task.

### Coverage
- Not applicable. No code paths were changed.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are td:0 pass-through; no `TestFromAC_*` classes or task-owned tests exist.

#### Security Review
- No issues. Deliverable is process guidance in kanban body plus follow-up task creation; no new execution, IO, auth, or persistence surface.

#### Test Integrity
- Not applicable. No task-owned test edits.

#### Test Quality
- Not applicable for td:0 non-implementation work.

#### Data Safety
- No issues observed.

#### Implementation-Aware Test Gap Analysis
- Not applicable. Deliverable is the calibration note in `.owlbear/kanban/tasks/1237-architect-calibration-dependency-graph-direction-and-infeasible-test-gates-in-fr.md` plus follow-up task `#1258`.

#### Necessity Check
- Not applicable. No dependency/integration/tool addition.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section only (`.owlbear/kanban/tasks/1237-architect-calibration-dependency-graph-direction-and-infeasible-test-gates-in-fr.md:118`). No prior `## Review Evidence` section found.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1. Calibration note covers the dependency-graph direction rule and suite-health pre-check rule | Current task note contains `Triggering case: task #1225` at `.owlbear/kanban/tasks/1237-architect-calibration-dependency-graph-direction-and-infeasible-test-gates-in-fr.md:103`, `Dependency-graph direction rule` at `:105`, and `Suite health pre-check rule` at `:109`. The cited trigger is grounded by archived task #1225: the incorrect direct-import AC is documented at `.owlbear/kanban/archive/1225-frontend-split-kanbanboard-into-card-column-board.md:186` and corrected dependency direction at `:224`; the infeasible durable-suite gate is documented at `:136-137` and `:173`. | N/A (td:0) | PASS |
| AC2. Calibration note references task #1225 as the triggering case | `.owlbear/kanban/tasks/1237-architect-calibration-dependency-graph-direction-and-infeasible-test-gates-in-fr.md:103` explicitly references `task #1225`, and archived task evidence confirms that #1225 is the triggering case (`.owlbear/kanban/archive/1225-frontend-split-kanbanboard-into-card-column-board.md:136-137`, `:186`, `:224`). | N/A (td:0) | PASS |
| AC3. Follow-up kanban tasks are created if a systemic fix is needed | Follow-up task exists as `.owlbear/kanban/tasks/1258-update-w-arch-review-enforce-import-chain-direction-suite-health-gate-checks.md:2`, is parented to `1237` at `:14`, and encodes both systemic fixes at `:25`, `:27`, and `:29`. | N/A (td:0) | PASS |

### Informational
- Minor task-body drift only: task #1237 says `#1258 (backlog)` at `.owlbear/kanban/tasks/1237-architect-calibration-dependency-graph-direction-and-infeasible-test-gates-in-fr.md:115` and `:124`, but live task `#1258` is currently `todo` at `.owlbear/kanban/tasks/1258-update-w-arch-review-enforce-import-chain-direction-suite-health-gate-checks.md:4`. AC3 requires creation of the systemic follow-up, not a specific status, so this does not block PASS.

### Deductions
-0.03 informational confidence deduction for task-body status drift on follow-up #1258 (`backlog` claimed in #1237, `todo` on live board).

### Verdict
- PASS
- Confidence: 0.95
- Action: advance to docs

### Post-task Reflection
- Process-only td:0 tasks still need independent evidence; `quality-runner` can legitimately return `not applicable` when the scope is justified.
- For calibration tasks, archived triggering-task evidence matters more than current task prose; the grounding here came from archived #1225, not builder self-report.
- Task-body self-reports can drift from live board state; reviewer should verify follow-up task existence and status directly rather than trusting the parent note.
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed-files set: `.owlbear/kanban/tasks/1237-*.md`, `.owlbear/kanban/tasks/1258-*.md` — kanban task body files; no IN-scope descriptive doc references these |
| 2 | Module docstrings | No | N/A | No Python source files modified |
| 3 | External attribution | No | N/A | No external patterns used; calibration is internal process note |
| 4 | Research doc | No | N/A | No research phase for this calibration task |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` glob `.owlbear/kanban/**` technically matches task files, but diagram depicts kanban service code architecture — not task body prose. No architectural change; footer update would be false-positive busywork |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1237-*.md` | OUT | N/A — kanban task body, not IN-scope doc |
| `.owlbear/kanban/tasks/1258-*.md` | OUT | N/A — kanban task body, not IN-scope doc |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for #1237)
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1. Calibration note covers dependency-graph direction rule and suite-health pre-check rule | Task body section "## Calibration Note (Architect)" at :101-115 contains both rules with concrete guidance. Reviewer cross-verified against archived #1225 evidence at :168. | PASS |
| AC2. Calibration note references task #1225 as triggering case | "Triggering case: task #1225" at :103. Reviewer verified against archived #1225 at :169. | PASS |
| AC3. Follow-up tasks created if systemic fix needed | #1258 exists (parent: #1237, status: in-progress), titled "Update w-arch-review: enforce import-chain direction + suite-health gate checks". Both systemic fixes encoded in AC. | PASS |

### Test Results
- pytest: 3425 passed, 105 failed, 4 skipped (all failures pre-existing; task has no code changes, all td:0)
- ruff: 4 violations, none in task-scoped files (pre-existing background debt)

### Architect Quality: 4/5
Clear, specific AC for a calibration task. Two concrete sub-rules, conditional follow-up requirement. Minor gap: deliverable location left flexible (task body or decisions entry), but appropriate for process artifact.

### Deduction Breakdown
- AC lines without evidence: 0 of 3, deduction -0.00
- Lint violations in task scope: 0, deduction -0.00
- AC quality score 4 (above 3): deduction -0.00
- Reviewer evidence section: present, detailed, PASS with line-level citations into archived #1225, deduction -0.00
- Full-suite failures in task scope: 0 (105 failures all pre-existing, no code changes), deduction -0.00
- Minor informational: #1258 cited as "backlog" in body but live as "in-progress" (non-blocking status drift), deduction -0.01

### Confidence: 0.99
### Action: archive