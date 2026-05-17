---
id: 1624
title: 'P3-02: Success feedback — PToast notifications'
status: review
priority: important
created: 2026-05-16T03:37:44.703987+00:00
updated: 2026-05-16T18:23:18.042461+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on: []
ac:
  - "Successful task-move (drag-drop or context-menu transition) triggers PToast:
    `p-toast-item[state='success']` appears with text containing target status name,
    within 500ms of response"
  - After a successful edit-only mutation in TaskFieldsEditor (not 
    release/unblock/move-backward via TaskActions), 
    `[data-testid='save-confirmed']` becomes visible; resets after 2000ms 
    (±500ms); does NOT appear on mutation error or non-edit mutations through 
    the same hook instance
  - "Mutation error and warning paths unchanged: both `p-banner[state='error'][open]`
    and `p-banner[state='warning'][open]` still render correctly after PToast addition;
    no regression on existing PBanner error/warning test suites"
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

PToast for move/mutation success, inline confirmation for edits.

Scope: Success feedback only.
Out of scope: Dark mode, focus-visible, motion, accessibility sweep.

2026-05-16T15:44:01+00:00
## Research
- Research doc: .owlbear/research/ptoast-success-feedback.md
- Sources: 8 studied, 6 high-relevance (≥0.85)
- Recommendation: PToast singleton in App.tsx, wired via Shell callbacks; inline edit confirmation via saved state in TaskFieldsEditor (confidence: 0.82)
- Follow-up tasks created: none needed — this task is the implementation task
- Decision requests: none (T1 — config/integration change)

## Challenge Results
- Challenger: reconsider → proceed after revisions (original: 0.48, revised: 0.82)
- Key challenges: (1) inline save resolves on error too — need explicit onMutationSuccess in useTaskMutation, (2) proof target is p-toast-item not p-toast host, (3) callback signature change is backwards-compatible, (4) mount PToast in App.tsx for lifecycle safety, (5) AC quality gap addressed with DOM contracts
- Researcher response: accepted all 5 — revised recommendation with concrete DOM contracts and success signal architecture

## Implementation Guidance
### PToast Mount
- `App.tsx`: add `<PToast />` inside `PorscheDesignSystemProvider`, before `<BrowserRouter>`
- Import: `PToast` from `@porsche-design-system/components-react`

### Move Success Toasts
- Shell.tsx: call `useToastManager().addMessage({ text, state: 'success' })` from onMutationSuccess
- Enhance `onMutationSuccess` from `() => void` to `(message?: string) => void`
- KanbanBoard: pass target status in message, e.g. `onMutationSuccess?.(\`Task moved to ${targetStatus}\`)`

### Inline Edit Confirmation
- Add `onMutationSuccess?: () => void` to `UseTaskMutationOptions` (called only on true success, line 97)
- DetailTab/TaskFieldsEditor: on success callback, set brief "Saved" indicator (data-testid="save-confirmed")
- Auto-reset after ~2s; does NOT use PToast per task body scope

### Error No-Regression
- PBanner error paths unchanged
- PToast is additive (separate PDS component, separate top-layer)

### DOM Contracts for Testing
- AC1: `p-toast-item` inside `p-toast` shadow DOM appears with success text within 500ms after move
- AC2: `[data-testid="save-confirmed"]` visible after edit save, not visible after error
- AC3: `PBanner[open=true]` still shows on mutation errors

[[2026-05-16T17:44:15+02:00]]
## Research
- Research doc: .owlbear/research/ptoast-success-feedback.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: PToast singleton in App.tsx + useToastManager in Shell; inline edit confirmation via saved state in TaskFieldsEditor (confidence: 0.82)
- Follow-up tasks: none — this is the implementation task
- Decision requests: none (T1)

## Challenge Results
- Challenger: reconsider → proceed after revisions
- Confidence revised: 0.48 → 0.82
- Key revisions: explicit onMutationSuccess in useTaskMutation for clean success signal, p-toast-item as proof target, PToast mount in App.tsx for lifecycle safety, concrete DOM contracts for all 3 ACs

2026-05-16T16:19:33+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Success feedback only; no error-path changes |
| Interface clarity | PASS | Refined AC names exact DOM selectors, timing, and scope boundaries |
| Dependency correctness | PASS | Dep #1619 archived (deprecated); tests will be written at todo stage by test-writer |
| Module layering | PASS | PToast mount in App.tsx (top), useToastManager in Shell (consumer), indicator in TaskFieldsEditor (leaf) |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer processes at todo |
| KISS/YAGNI | PASS | Singleton mount + callback enhancement; no new context/provider layer |
| Premise challenge | PASS | No existing PDS success feedback; PToast is the sanctioned PDS mechanism |
| Pattern consistency | PASS | Follows existing PBanner error pattern (component mount + hook usage) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| useToastManager before PToast mount | querySelector returns null | Runtime warning from PDS | Yes — mount in App.tsx guarantees availability | Console warning, no toast shown |
| Save-confirmed on non-edit mutation | Hook-level callback fires broadly | N/A (logic bug) | AC2 scopes to edit-only; see guidance revision below | False positive indicator |

### Implementation Guidance Revision (from arch review)
The research doc recommends adding `onMutationSuccess` to `UseTaskMutationOptions`, but the challenger correctly identified that `runMutation` serves edit, release, AND move paths from a single hook instance. The AC2 scope constraint (\"edit-only\") means the builder must scope the indicator at the CALL SITE:

**Recommended approach:** Have `runMutation` return a success signal (`Promise<boolean>` or resolve without throwing = success). TaskFieldsEditor checks the return and triggers save-confirmed only from its own edit call site. This avoids the hook-level callback entirely for the indicator — no `onMutationSuccess` on UseTaskMutationOptions needed.

Alternatively: pass an optional `context` arg to runMutation and only fire the indicator when context matches 'edit'. Builder's choice — AC constrains behavior, not mechanism.

### Design Diverge
- Trigger: skipped — single valid approach (Option B-revised from research)

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Key findings: (1) critical — hook-level onMutationSuccess scope too broad for AC2; (2) AC1 trigger coverage; (3) AC3 omits warning path; (4) ~2s approximation; (5) conflict-retry save path
- Architect response: accepted findings 1,2,3,4. AC refined to address all. Finding 5 (conflict-retry) is implicitly covered — \"edit-only mutation in TaskFieldsEditor\" includes force-save via same UI. Added guidance revision for scoping mechanism.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC with PDS DOM contracts, scoped edit-only trigger, warning no-regression. Appended implementation guidance revision for hook-scope mitigation. Advancing to todo.

[[2026-05-16T18:19:40+02:00]]
Architecture review complete. Refined all 3 AC lines with exact PDS DOM selectors, scope boundaries, and timing constraints. Addressed challenger critical finding (hook-level callback scope) by adding guidance revision — builder scopes indicator at call site, not hook options. Proof bundle: behavioral confirmed.

[[2026-05-16T19:21:18+02:00]]
## Test-Writer Notes

**Test files:**
- `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx`
- `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`

**Classes and test breakdown:**

| Class | Category | Count |
|-------|----------|-------|
| `TestFromAC_KanbanBoardMoveMessage` | happy (2) | 2 |
| `TestFromAC_ShellToastFeedback` | happy (3) | 3 |
| `TestFromAC_PToastMount` | happy (2) | 2 |
| `TestFromAC_PBannerNoRegression` | regression (3) | 3 |
| `TestFromAC_SaveConfirmed` | happy (2), boundary (1), edge (3) | 6 |

**Total: 16 tests, 16 FAIL** (confirmed via `npm exec vitest run`)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 — KanbanBoard passes target status in onMutationSuccess | `TestFromAC_KanbanBoardMoveMessage` (2 tests: drag-drop, context-menu) |
| AC1 — Shell calls useToastManager.addMessage with state=success | `TestFromAC_ShellToastFeedback` (3 tests) |
| AC1 — App mounts PToast inside PorscheDesignSystemProvider | `TestFromAC_PToastMount` (2 tests) |
| AC2 — save-confirmed visible after edit save, resets after 2000ms, absent on error | `TestFromAC_SaveConfirmed` (6 tests) |
| AC3 — PBanner error/warning no regression alongside PToast | `TestFromAC_PBannerNoRegression` (3 tests) |

**Failure evidence:** `Tests  16 failed (16)` — commit dd58ca5d

**DOM contracts tested:**
- `p-toast-item[state='success']` via `useToastManager.addMessage({ state: 'success', text: ... })` mock
- `[data-testid='save-confirmed']` presence/absence and timing (fake timers)
- `[data-testid='ptoast-stub']` in App DOM tree
- `[data-testid='pbanner-stub']` coexistence with PToast

[[2026-05-16T20:23:18+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/App.tsx, serve/cockpit/web/src/Shell.tsx, serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/TaskFieldsEditor.tsx.
- AC1: KanbanBoard now passes target-status message on successful move (`Task moved to ${targetStatus}`); Shell consumes message via `useToastManager().addMessage({ state: 'success', text: message })`; PToast host is mounted in Shell and present in App render tree.
- AC2: TaskFieldsEditor now shows `[data-testid="save-confirmed"]` only after successful edit-path save and auto-resets at 2000ms; indicator is suppressed for error paths and non-dirty/non-edit confirmation scenarios.
- AC3: Existing PBanner error/warning behavior preserved while adding toast success flow.
- Quality-runner: initial scoped runs were unstable with environment errors (`HTMLElement is not defined`); retried once per protocol, then used direct frontend fallback commands.
- Verification (direct fallback evidence):
  - `npm exec vitest run src/__tests__/PToastSuccess_1624.test.tsx src/__tests__/SaveConfirmed_1624.test.tsx --reporter=verbose` -> exit 0, task tests passing (16/16).
  - `npm exec eslint -- src/App.tsx src/Shell.tsx src/KanbanBoard.tsx src/components/TaskFieldsEditor.tsx src/__tests__/PToastSuccess_1624.test.tsx src/__tests__/SaveConfirmed_1624.test.tsx` -> exit 0, lint clean.
  - `npm exec vitest run src/__tests__/Shell.pbanner-1498.test.tsx src/__tests__/KanbanBoard.pbanner-1498.test.tsx src/__tests__/DetailTab.pbanner-1498.test.tsx --reporter=verbose` -> exit 0, regression suite passing (30/30).
- Commit: 17b48844 (`feat: add success feedback via ptoast and save confirmation (#1624, builder)`).
