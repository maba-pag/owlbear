---
id: 1238
title: 'Closeout: Archival UX in Cockpit — verify all child tasks complete'
status: todo
priority: important
created: 2026-05-01T03:04:34.449352+00:00
updated: 2026-05-01T07:34:35.547857+00:00
tags:
- quality
parent:
depends_on:
- 1244
- 1246
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Summary

Extend the Cockpit `→ archived` flow to collect and persist `archival_reason` and
`archival_refs`. Currently every human-initiated archive lands with
`archival_reason=None` / `archival_refs=[]`, breaking downstream dependency resolution.

**Scope:** `existing-feature/refactor` — engine and cockpit view are complete.
Gaps: `MoveRequest`, move route, `CockpitView.move_task` (no validation block), and
frontend (`handleTransitionClick`, new `ArchivalModal` component).

## Brief

See `.owlbear/briefs/draft-archival-ux/brief.md` for the full specification including
backend changes (B1–B3), frontend changes (F1–F3), acceptance criteria, out-of-scope
boundaries, and known limitations.

[[2026-05-01]]
## Planning

**8 subtasks created** across 2 domains (backend + frontend), 3 dependency layers.

| ID | Title | Priority | Deps | Tags |
|----|-------|----------|------|------|
| #1239 | Test: MoveRequest archival fields and route pass-through | needed | — | scope:backend |
| #1240 | Test: CockpitView archival validation block | needed | — | scope:backend |
| #1241 | Test: ArchivalModal component | needed | — | scope:frontend |
| #1242 | Test: handleTransitionClick archive intercept | needed | — | scope:frontend |
| #1243 | Implement: MoveRequest archival fields and route pass-through | needed | #1239 | scope:backend |
| #1244 | Implement: CockpitView archival validation block | important | #1240, #1243 | scope:backend |
| #1245 | Implement: ArchivalModal component and ARCHIVAL_REASONS constant | needed | #1241 | scope:frontend |
| #1246 | Implement: handleTransitionClick archive intercept | important | #1242, #1245 | scope:frontend |

**Dependency layers:**
- Layer 1 (parallel): #1239, #1240, #1241, #1242 (all test tasks, no deps)
- Layer 2 (parallel): #1243 (after #1239), #1245 (after #1241)
- Layer 3 (parallel): #1244 (after #1240 + #1243), #1246 (after #1242 + #1245)

Backend and frontend tracks are independent — can run concurrently after layer 1.

**Decomposition notes:**
- B1+B2 paired (#1239/#1243): simple and tightly coupled, no justification for a split
- B3 owns its own pair (#1240/#1244): 10+ validation cases, the most complex backend task
- F1+F2 paired (#1241/#1245): ARCHIVAL_REASONS is a dependency of ArchivalModal, trivial to co-locate
- F3 owns its own pair (#1242/#1246): depends on ArchivalModal existing

[[2026-05-01]]
## Test-Writer Notes
- Non-implementation parent/orchestration task — no AC, no testable interface.
- All test work is in subtasks #1239, #1240, #1241, #1242.
- Passing through to builder.
[[2026-05-01]]
## Builder Notes
- Non-implementation parent/orchestration task confirmed from test-writer notes.
- No source files changed.
- No tests or lint run (not applicable for pass-through parent task).
- Passing through to review per w-tdd-green Step 0a.
[[2026-05-01]]
## Review Evidence
### Changed Scope
- Parent task body still carries the original feature scope and split plan rather than closeout criteria: `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:19-62`.
- The same parent body then pass-throughs reviewability by note only: test-writer and builder mark it non-implementation with no parent AC/tests at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:64-74`.
- No prior `## Review Evidence` section existed in task #1238 before this note, so this is the first review failure.
- Live child-task state shows the split work is still active:
  - `#1241` is `in-progress` at `.owlbear/kanban/tasks/1241-test-archivalmodal-component.md:4`
  - `#1242` is `review` at `.owlbear/kanban/tasks/1242-test-handletransitionclick-archive-intercept.md:4`
  - `#1243` is `in-progress` at `.owlbear/kanban/tasks/1243-implement-moverequest-archival-fields-and-route-pass-through.md:4`
  - `#1244` is `todo` at `.owlbear/kanban/tasks/1244-implement-cockpitview-archival-validation-block.md:4`
  - `#1245` is `todo` at `.owlbear/kanban/tasks/1245-implement-archivalmodal-component-and-archival-reasons-constant.md:4`
  - `#1246` is `todo` at `.owlbear/kanban/tasks/1246-implement-handletransitionclick-archive-intercept.md:4`
  - `#1239` is archived per live kanban lookup.

### Test Results
- `quality-runner` empty-scope check for task `#1238`: tests `not_applicable=true`; no execution error.

### Lint
- `quality-runner` empty-scope check for task `#1238`: lint `not_applicable=true`; no execution error.

### Coverage
- Not applicable. The parent task has no builder-owned code changes and no task-owned test scope.

### Pass 1 - CRITICAL
#### Split-Parent Routing / Reviewability
- FAIL: this parent was passed through as a non-implementation task without first being rewritten as a closeout/tracking task.
- Evidence: the parent still describes the full original feature and all eight split subtasks at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:19-62`, while multiple children remain unfinished (`#1241`, `#1242`, `#1243`, `#1244`, `#1245`, `#1246`).
- A split parent is not reviewable in this state. Passing it here would be a false green on work that has explicitly been delegated to child tasks.

#### Test-Writer AC Coverage
- No parent-specific AC or task-owned `TestFromAC_*` suite exists. That is only acceptable after the parent is rewritten to explicit closeout criteria. In the current state it leaves the reviewer with no reviewable parent contract.

#### Security Review
- No separate parent-code surface exists to review. No blocking security issue observed in the parent scope.

#### Test Integrity
- N/A on the parent task. No parent-owned `TestFromAC_*` tests exist.

#### Test Quality
- FAIL structurally: there is no executable parent proof because the task body was not converted from the original feature brief into closeout criteria after the split.

#### Data Safety
- N/A on the parent task.

#### Implementation-Aware Test Gaps
- Not applicable to the parent task itself. The blocking defect is lifecycle/routing, not a missing branch in a reviewed implementation file.

#### Necessity Check
- N/A.

#### Builder Process Quality
- CLEAN: one pass-through builder section only; no retry loop or weakened tests.

### AC Compliance
| Reviewability Gate | Evidence | Mapped Test | Status |
|---|---|---|---|
| Parent task must have a reviewable closeout contract before downstream pass-through | Parent still carries the original split feature scope at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:19-62`; child tasks remain active at the status lines cited above; no parent-owned test file or closeout criteria exists. | None | FAIL |

### Deductions
- `-0.12` parent was not rewritten as a closeout/tracking task after the split.
- `-0.06` multiple child tasks are still active, so a parent PASS here would be a false green.

### Verdict
- FAIL -> `backlog`
- Confidence: `0.82`
- Reason: routing/contract failure. The parent reached review before the split child tasks completed and before the parent was rewritten into a td:0 closeout task.

### Required Follow-up
- Rewrite `#1238` as a closeout/tracking task only after the split children finish, or keep it out of downstream review until that rewrite happens.
- Replace the current original-feature body with explicit parent closeout criteria; the current body at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:19-74` is not a valid downstream pass-through contract.
- Re-enter review only once the parent has an actual closeout contract or is otherwise removed from the downstream implementation path.

### Action
- Reject to `backlog` for architect/orchestrator correction.

## Post-task Reflection
- Split parents are especially prone to false-green pass-through if the body is left as the original feature scope.
- Empty-scope quality-runner runs are only evidence of N/A, not evidence that a parent task is valid for PASS.
- The decisive proof for this class of defect is the combination of parent-body scope lines and live child status lines.
[[2026-05-01]]

## Closeout Criteria

**This is a closeout/tracking task.** All implementation work is in subtasks #1239–#1246.
The original feature scope in the Summary/Brief/Planning sections below is retained for
audit trail only — the binding contract is this Closeout Criteria section.

### Acceptance Criteria

- [ ] All child test tasks are `done` or `archived`: #1239, #1240, #1241, #1242 (td:0)
- [ ] All child implementation tasks are `done` or `archived`: #1243, #1244, #1245, #1246 (td:0)
- [ ] Brief outcomes in `.owlbear/briefs/draft-archival-ux/brief.md` are satisfied by child task completion — spot-check at least backend B1–B3 and frontend F1–F3 (td:0)

### Test-writer: SKIP

All AC lines are td:0. No task-owned tests needed.

## Architecture Review

**Verdict:** REFINE → APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Child test tasks done/archived | td:0, verifiable by kanban status check | No change |
| Child impl tasks done/archived | td:0, verifiable by kanban status check | No change |
| Brief outcomes spot-check | td:0, verifiable by reading brief + child evidence | No change |

### Architecture Notes

- Reviewer correctly rejected the previous pass-through: the parent carried the original
  feature scope as its body, causing test-writer and builder to false-pass-through on
  implementation AC that was delegated to children.
- Rewritten as a closeout task per the split-parent closeout pattern. Title updated to
  signal closeout role. `quality` tag added for test-writer pass-through.
- Dependencies added on terminal leaf tasks #1244 and #1246 — these imply all upstream
  tasks (#1239, #1240, #1241, #1242, #1243, #1245) are also complete.
- No codebase changes at parent level. No security surface. No new interfaces.

### Dependency Analysis

- `depends_on: [#1244, #1246]` — leaf implementation tasks. Their own deps (#1239, #1240,
  #1241, #1242, #1243, #1245) must complete first, creating the full dependency chain.
- This task will not be dispatchable until both terminal children reach `done`.

### Challenger

Challenge: SKIP — all AC lines are td:0, per Step 2.1 gating rule.
[[2026-05-01]]
REFINE → APPROVE. Rewritten as closeout/tracking task per split-parent closeout pattern. Title updated, `quality` tag added, closeout AC (all td:0) appended, dependencies set on terminal leaf tasks #1244 and #1246. Original feature scope retained for audit trail. Test-writer: SKIP. Challenger: SKIP (td:0 gating).