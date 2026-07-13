---
id: 1238
title: 'Closeout: Archival UX in Cockpit — verify all child tasks complete'
status: archived
priority: medium
created: 2026-05-01T03:04:34.449352+00:00
updated: 2026-05-02T07:23:54.533344+00:00
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
[[2026-05-02]]
## Test-Writer Notes
- Non-implementation pass-through: task tagged `quality`, all AC lines are `td:0`.
- Explicit `### Test-writer: SKIP` directive in task body confirms no tests needed.
- Retry context: reviewer had rejected prior pass-through because the parent body still carried original feature scope. Architect rewrote the body as a proper closeout task with explicit td:0 AC before re-dispatch.
- No task-owned tests written or applicable.
- Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Non-implementation closeout/tracking task confirmed (`quality` tag, all AC lines are td:0, explicit test-writer SKIP).
- No source files changed.
- Child completion evidence (all archived): #1239, #1240, #1241, #1242, #1243, #1244, #1245, #1246.
- Brief spot-check completed against `.owlbear/briefs/draft-archival-ux/brief.md`: backend outcomes B1-B3 and frontend outcomes F1-F3 are delegated to, and covered by, the archived child implementation chain.
- Tests/Lint/Coverage: not applicable for this parent closeout pass-through; no task-owned implementation surface.

## Post-task Reflection
- For split-parent closeout tasks, explicit child-status verification prevents false-green pass-through.
- `show_task` may return not-found for archived children; `list_tasks(archived=true, search=ID)` is the reliable verification fallback.
- td:0 closeout AC should be treated as evidence collection work (task state + brief traceability), not execution work.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped td:0 check: tests not applicable; no execution error.

### Lint
- quality-runner scoped td:0 check: lint not applicable for empty task-owned scope.
- VS Code diagnostics: no errors in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, or `serve/cockpit/web/src/KanbanBoard.tsx`.

### Coverage
- Not applicable. Parent task `#1238` owns no source or test files; the binding contract is the td:0 closeout criteria at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:167-173`.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- N/A by contract. Parent task explicitly marks all AC lines td:0 and `### Test-writer: SKIP` at `.owlbear/kanban/tasks/1238-archival-ux-in-cockpit-collect-and-persist-archival-metadata-on-human-initiated-.md:167-173`.

#### Security Review
- No new parent-level code surface exists.
- Live archival UX spot-check shows the reviewed child work is still present in the current workspace: request fields and route pass-through in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:42-43,161-166`; archival validation and engine forwarding in `serve/cockpit/src/owlbear_cockpit/view.py:120-165,248-259`; frontend archival modal and a11y path in `serve/cockpit/web/src/components/ArchivalModal.tsx:10-14,84,163-175,200-221,238`; archive intercept + frozen `expectedUpdated` handoff in `serve/cockpit/web/src/KanbanBoard.tsx:157-161,209,237-238`.
- No blocking security issue observed in the closeout scope.

#### Test Integrity
- N/A on the parent task. No parent-owned `TestFromAC_*` suite exists or is required for td:0 closeout AC.

#### Test Quality
- N/A on the parent task. This review is evidence collection against td:0 closeout criteria, not executable parent-proof.

#### Data Safety
- No new parent-owned mutation path. Spot-checked live backend/frontend archival flow matches the approved child implementation chain.

#### Implementation-Aware Test Gaps
- No closeout evidence gap found. The parent AC asks for child completion plus a brief-to-live-code spot-check, and both are satisfied.

#### Necessity Check
- N/A. No new dependency, integration, or external capability is introduced by this parent closeout task.

#### Builder Process Quality
- CLEAN. This is the second review cycle, but the first failure was resolved by an intervening architecture rewrite that converted the parent into a valid closeout task before re-dispatch. No retry loop or weakened-proof pattern remains.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All child test tasks are `done` or `archived` | Archived child test tasks verified directly: `.owlbear/kanban/archive/1239-test-moverequest-archival-fields-and-route-pass-through.md:4`, `.owlbear/kanban/archive/1240-test-cockpitview-archival-validation-block.md:4`, `.owlbear/kanban/archive/1241-test-archivalmodal-component.md:4`, `.owlbear/kanban/archive/1242-test-handletransitionclick-archive-intercept.md:4` | N/A (td:0) | PASS |
| All child implementation tasks are `done` or `archived` | Archived child implementation tasks verified directly: `.owlbear/kanban/archive/1243-implement-moverequest-archival-fields-and-route-pass-through.md:4`, `.owlbear/kanban/archive/1244-implement-cockpitview-archival-validation-block.md:4`, `.owlbear/kanban/archive/1245-implement-archivalmodal-component-and-archival-reasons-constant.md:4`, `.owlbear/kanban/archive/1246-implement-handletransitionclick-archive-intercept.md:4` | N/A (td:0) | PASS |
| Brief outcomes in `.owlbear/briefs/draft-archival-ux/brief.md` are satisfied by child task completion; spot-check backend B1-B3 and frontend F1-F3 | Brief sections: `.owlbear/briefs/draft-archival-ux/brief.md:63,75,80,99,110,163`. Live code matches them: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:42-43,161-166` for B1-B2; `serve/cockpit/src/owlbear_cockpit/view.py:120-165,248-259` for B3; `serve/cockpit/web/src/components/ArchivalModal.tsx:10-14,84,163-175,200-221,238` for F1-F2; `serve/cockpit/web/src/KanbanBoard.tsx:157-161,209,237-238` for F3 | N/A (td:0) | PASS |

### Informational
- `show_task` does not surface archived children; archive files are the reliable source of truth for this closeout pattern.
- No editor diagnostics are present in the spot-checked live backend/frontend files.

### Deductions
- None.

### Verdict
- PASS -> `docs`
- Confidence: `0.96`
- Reason: the rewritten td:0 closeout contract is valid, all eight child tasks are archived, and the live backend/frontend implementation still matches brief outcomes B1-B3 and F1-F3.

### Action
- Advance to `docs`.

## Post-task Reflection
- Split-parent closeout review is strongest when it cites archive files directly rather than relying on `show_task`, which excludes archived entries.
- td:0 parent tasks still need live-code spot-checks when the AC explicitly traces back to a brief outcome.
- Frontend closeout checks benefit from pairing quality-runner N/A evidence with VS Code diagnostics, since quality-runner does not cover TypeScript linting.
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` mutation table omitted `ValidationError → 422` for archival move failures; added |
| 2 | Module docstrings | No | N/A | `mutation.py` and `view.py` docstrings are accurate; no false claims |
| 3 | External attribution | No | N/A | Closeout/tracking task; no external patterns used |
| 4 | Research doc | No | N/A | No research phase for this closeout task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**,serve/cockpit/web/src/**`; footer updated from `791c7f37` → `5dcad22c` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | IN (docstrings) | Checked — accurate, N/A |
| `serve/cockpit/src/owlbear_cockpit/view.py` | IN (docstrings) | Checked — accurate, N/A |
| `serve/cockpit/web/src/components/ArchivalModal.tsx` | OUT | TypeScript — no edit |
| `serve/cockpit/web/src/KanbanBoard.tsx` | OUT | TypeScript — no edit |
| `serve/cockpit/README.md` | IN | Updated (Item 1) |
| `share/diagrams/cockpit.excalidraw` | IN | Updated (Item 5) |

### Files Updated

- `serve/cockpit/README.md` — added `ValidationError → 422` to move_task route Notes cell
- `share/diagrams/cockpit.excalidraw` — footer updated to `Last verified: 2026-05-02 (5dcad22c)`

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1238-*` files found)

Commit: `d5b94f21` — docs: add ValidationError→422 to move_task route, update cockpit diagram footer (#1238, doc-writer)
[[2026-05-02]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All child test tasks done/archived (#1239-#1242) | All 4 files present in `.owlbear/kanban/archive/` | PASS |
| All child impl tasks done/archived (#1243-#1246) | All 4 files present in `.owlbear/kanban/archive/` | PASS |
| Brief outcomes spot-check (B1-B3, F1-F3) | Implementation commits: `77ef875d` (B1-B2), `2e707acb` (B3), `36e19cdf` (B3 fix). Doc-writer commit: `d5b94f21`. Frontend child tasks archived with reviewer PASS. | PASS |

### Test Results
- pytest (tests/, excluding known-hanging #1234/#1262 events tests): 1630 passed, 76 failed, 4 skipped
- All 76 failures in unrelated tasks: #1267 (4), #1269 (10), #1199 (2), #1176 (11) plus duplicates. Zero failures in #1238 scope.
- Task-scoped backend tests (1239/1240/1243/1244): 53 passed, 0 failed
- ruff (tests/ + serve/cockpit/): clean

### Architect Quality: 4/5
Closeout rewrite after reviewer rejection was well-structured. td:0 AC lines are specific and verifiable. Dependencies on terminal leaf tasks (#1244, #1246) correctly imply full chain completion. Minor: initial dispatch as feature-scope parent required a reject cycle before correction.

### Deduction Breakdown
- No AC lines without evidence: 0
- Lint: clean: 0
- AC quality 4/5: 0
- Reviewer evidence present and detailed (PASS at .96): 0
- Full-suite failures outside task scope: 0

### Confidence: .98
### Action: archive