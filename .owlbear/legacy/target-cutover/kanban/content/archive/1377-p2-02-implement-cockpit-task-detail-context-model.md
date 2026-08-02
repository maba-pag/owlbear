---
id: 1377
title: 'P2-02: Implement Cockpit task detail context model'
status: archived
priority: medium
created: 2026-05-06T01:04:31.145299+00:00
updated: 2026-05-08T16:45:14.096349+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- model
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the Cockpit task detail frontend model needed for safe detail-view decisions.

## Problem Evidence
- DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by.
- Dependency and parent context is not available enough for action gating and edit decisions.
- Missing context can be confused with a user clearing a value.

## Acceptance Criteria
- The task detail frontend model matches backend task detail fields needed for Cockpit decisions, including claim state.
- Dependency and parent context from the backend is preserved for UI decisions wherever the backend exposes it.
- Optional or unavailable context has an explicit state and is not converted into a clearing edit.
- Existing valid task fetch, edit, and move flows continue to work with the expanded model.
- The implementation satisfies #1376 without adding action-gating or validation behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail model, parsing, and state propagation.
- Out of scope: edit validation, dirty-state UX, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1376.

[[2026-05-08]]
## Architecture Review

### Verdict: REJECT

### Findings

1. **Dependency #1376 (test task) does not exist.** The task declares `depends_on: [1376]` and references "Test task: #1376" but no task with that ID exists on the board. The TDD pipeline cannot function without its RED-phase counterpart.

2. **Problem Evidence is stale.** The frontend `TaskDetail` interface (DetailTab.tsx L16-31) already includes:
   - `claimed: boolean`
   - `claimed_at: string | null`
   - `dep_status: string | null`
   - `parent: number | null`
   - `depends_on: number[]`
   
   The task claims "DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by" — this is factually incorrect for `claimed` and `claimed_at`.

3. **`claimed_by` is deliberately omitted by the backend.** The kanban engine's `TaskSummary._coerce_claimed` validator (models.py L497-505) explicitly `data.pop("claimed_by", None)`. The field is never exposed in the API response. The frontend cannot model a field the backend deliberately drops.

4. **AC may already be satisfied.** Given that the frontend model already has claim state, dependency context, and parent context — all typed as `T | null` (explicit absent state, not `undefined`) — the AC lines appear to describe current behavior.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused on model expansion |
| Interface clarity | FAIL | AC references fields ("needed for Cockpit decisions") without specifying which are actually missing |
| Dependency correctness | FAIL | #1376 does not exist |
| TDD compliance | FAIL | Test task missing from board |
| Premise challenge | FAIL | Frontend model already has the claimed/dependency fields cited as missing |

### Required Research
- Identify what fields are genuinely missing from the frontend model vs the backend response (candidates: `archival_reason`, `archival_refs`, `guidance`, `missing_sections`)
- Determine whether any of those are needed for "safe detail-view decisions"
- Create the test task or redefine the dependency chain
- Rewrite Problem Evidence to reflect the current codebase state
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1377-task-detail-context-model.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Close as no-op (confidence: 0.95)

### Key findings
1. Task #1376 (the TDD test counterpart) was completed and archived — including the GREEN implementation (commit 216061a8) that added claim/dep_status fields to DetailTab.tsx.
2. All 15 tests in TaskDetailModel_1376.test.tsx pass against the current codebase.
3. Frontend TaskDetail already has every field the AC describes as "missing": claimed, claimed_at, dep_status, parent, depends_on.
4. Backend-only extras (archival_reason, archival_refs, guidance, missing_sections) are not needed for detail-view decisions.
5. #1377 is a no-op — its work was done during #1376's pipeline traversal.

### Follow-up
- Remove #1377 from #1378's depends_on to unblock Phase 2 downstream chain.
- Archive #1377 — no implementation changes needed.
[[2026-05-08]]
## Architecture Review (2nd pass)

### Verdict: APPROVE (no-op)

### AC Assessment (all td:0)

| AC Line | Assessment | Depth |
|---------|-----------|-------|
| Frontend model matches backend fields for claim state | ALREADY SATISFIED — `TaskDetail` in DetailTab.tsx L16-31 has `claimed: boolean`, `claimed_at: string \| null` | td:0 |
| Dependency/parent context preserved | ALREADY SATISFIED — `dep_status: string \| null`, `parent: number \| null`, `depends_on: number[]` present | td:0 |
| Optional context has explicit state, not clearing edit | ALREADY SATISFIED — all nullable fields typed as `T \| null`, never `undefined` | td:0 |
| Existing flows continue to work | ALREADY SATISFIED — 15/15 tests pass in TaskDetailModel_1376.test.tsx | td:0 |
| Satisfies #1376 without adding action-gating | ALREADY SATISFIED — #1376 was completed and archived with GREEN commit 216061a8 | td:0 |

### Architecture Notes
- All AC was implemented during #1376's pipeline traversal (GREEN phase, commit 216061a8).
- Field-by-field comparison of frontend `TaskDetail` vs backend `ShowTaskResponse` shows zero gaps for decision-relevant fields.
- Backend-only fields (`archival_reason`, `archival_refs`, `guidance`, `missing_sections`) are not needed for detail-view decisions.
- Removed stale `depends_on: [1376]` — #1376 is archived/done.

### Test-writer: SKIP
All AC lines are td:0. No implementation or test work needed.

### Follow-up (orchestrator)
- Remove #1377 from #1378's `depends_on` to unblock Phase 2 downstream chain.
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Architecture Review (2nd pass) verdict: APPROVE (no-op). All AC was already implemented during #1376's pipeline traversal (GREEN commit 216061a8).
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task — all AC lines are td:0 and already satisfied by prior pipeline work.
- Files changed: none.
- Tests run in this builder pass: none (pass-through per td:0 no-op contract).
- Coverage: not applicable (no code changes).
- ruff: not run (no code changes).
- Evidence summary: Architecture Review (2nd pass) marked no-op APPROVE; Test-Writer Notes explicitly indicate pass-through to builder.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner was not executed directly for this review. The latest task-local Architecture Review marks every AC line as `td:0` / already satisfied, and the current scoped quality-runner contract in this workspace does not support a meaningful lint-only td:0 review surface.
- Supporting historical evidence from archived counterpart task `#1376` remains green:
  - `.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:378` records a quality-runner scoped frontend run with 63 passed, 0 failed, 0 skipped across `TaskDetailModel_1376.test.tsx` and `DetailTab.test.tsx`.
  - `.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:384` records ESLint clean for `DetailTab.tsx` and the related tests.
  - `.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:389` records `DetailTab.tsx` coverage at 92.38% statements and 91.07% lines.
- Current workspace diagnostics are clean for `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/view.py`, and `serve/kanban/src/owlbear_kanban/models.py`.

### Lint
- Not run directly in this td:0 review.
- Supporting archived `#1376` review evidence is clean, and current workspace diagnostics show no live-file errors in the relevant frontend/backend surfaces.

### Coverage
- Not applicable for this task cycle; builder notes for `#1377` state `Files changed: none`.
- Supporting archived `#1376` coverage: `DetailTab.tsx` 92.38% statements, 91.07% lines.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- N/A for `#1377` itself. The latest task-local architecture refinement classifies every AC line as `td:0` already satisfied (`.owlbear/kanban/tasks/1377-p2-02-implement-cockpit-task-detail-context-model.md:106-114`). I verified that refined contract against the live frontend/backend code and the archived `#1376` evidence trail.

#### Security Review
- No security issues found in scope. The live surface is field projection plus read-only rendering only.

#### Test Integrity
- N/A. `#1377` has no task-local `TestFromAC_*` suite and builder notes report `Files changed: none` in this review cycle (`.owlbear/kanban/tasks/1377-p2-02-implement-cockpit-task-detail-context-model.md:134-139`).

#### Test Quality
- Supporting `#1376` proof package remains adequate for the underlying implementation: exact-value assertions for `claimed`, `claimed_at`, and `dep_status`, plus a dedicated field-sensitivity test are recorded in the archived task review (`.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:402-406`).

#### Data Safety
- No data-safety issue found in scope.

#### Implementation-Aware Gaps
- No significant gap found.
- Backend read surface: `TaskSummary` exposes `claimed_at`, `claimed`, `dep_status`, `parent`, and `depends_on`, while `_coerce_claimed` explicitly drops `claimed_by` (`serve/kanban/src/owlbear_kanban/models.py:459-503`). `ShowTaskResponse` extends that surface (`serve/kanban/src/owlbear_kanban/models.py:606-616`).
- Frontend detail model: `TaskDetail` includes `claimed`, `claimed_at`, `dep_status`, `parent`, and `depends_on` (`serve/cockpit/web/src/components/DetailTab.tsx:16-31`).
- Fetch/state propagation: `Shell` loads `/api/tasks/{id}` and stores the JSON response as `TaskDetail` (`serve/cockpit/web/src/Shell.tsx:85-121`).
- Edit/move/release response preservation: Cockpit mutation routes all return `SingleTaskResponse`, and `CockpitView._to_single_response()` builds that response from `task.model_dump()` so the expanded detail fields remain on mutation responses (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:142-173`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:272-319`, `serve/cockpit/src/owlbear_cockpit/view.py:67-75`).
- Optional-state handling: `DetailTab` keeps `claimed_at` / `dep_status` read-only in the UI (`serve/cockpit/web/src/components/DetailTab.tsx:253-255`), does not send them in edit payloads (`serve/cockpit/web/src/components/DetailTab.tsx:157-180`), and only clears `parent` through an explicit `null` produced by `parseParent()` (`serve/cockpit/web/src/components/DetailTab.tsx:96-103`, `serve/cockpit/web/src/components/DetailTab.tsx:162-165`). The backend edit contract distinguishes omit from null in `EditRequest` / `_build_edit_kwargs()` (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:39-60`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:176-210`).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- The top-level Problem Evidence in `#1377` is stale, but the latest task-local Architecture Review (2nd pass) refines the binding contract to a td:0 no-op and states a field-by-field comparison against backend `ShowTaskResponse` found zero decision-relevant gaps (`.owlbear/kanban/tasks/1377-p2-02-implement-cockpit-task-detail-context-model.md:102-123`). I treated the stale original framing as a confidence deduction, not a blocking defect.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| The task detail frontend model matches backend task detail fields needed for Cockpit decisions, including claim state | Backend `TaskSummary` / `ShowTaskResponse` expose `claimed_at`, `claimed`, `dep_status`, `parent`, and `depends_on`, and explicitly drop `claimed_by` (`serve/kanban/src/owlbear_kanban/models.py:459-503`, `serve/kanban/src/owlbear_kanban/models.py:606-616`). Frontend `TaskDetail` matches those decision-relevant fields (`serve/cockpit/web/src/components/DetailTab.tsx:16-31`). | PASS |
| Dependency and parent context from the backend is preserved for UI decisions wherever the backend exposes it | `Shell` fetches `/api/tasks/{id}` into `TaskDetail` (`serve/cockpit/web/src/Shell.tsx:85-121`). `DetailTab` stores `depends_on` and `parent` in component state and sends them back explicitly on save (`serve/cockpit/web/src/components/DetailTab.tsx:59-70`, `serve/cockpit/web/src/components/DetailTab.tsx:157-180`). Mutation routes return `SingleTaskResponse` via `task.model_dump()` (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:142-173`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:272-319`, `serve/cockpit/src/owlbear_cockpit/view.py:67-75`). | PASS |
| Optional or unavailable context has an explicit state and is not converted into a clearing edit | Backend response models make the optional fields explicit (`claimed_at: str | None`, `dep_status: str | None`, `parent: int | None`, `depends_on: list[int]`) (`serve/kanban/src/owlbear_kanban/models.py:459-503`). Frontend keeps those as nullable/explicit fields (`serve/cockpit/web/src/components/DetailTab.tsx:16-31`), renders `claimed_at` / `dep_status` read-only (`serve/cockpit/web/src/components/DetailTab.tsx:253-255`), and never sends them in edit payloads (`serve/cockpit/web/src/components/DetailTab.tsx:157-180`). `parent` clearing is explicit `null`, not accidental omission (`serve/cockpit/web/src/components/DetailTab.tsx:96-103`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:39-60`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:176-210`). | PASS |
| Existing valid task fetch, edit, and move flows continue to work with the expanded model | Read route returns `ShowTaskResponse` (`serve/cockpit/src/owlbear_cockpit/routes/read.py:124-127`). Edit/move/release routes return `SingleTaskResponse` (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:142-173`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:272-319`). Archived `#1376` quality-runner evidence shows 63 passed / 0 failed for the scoped frontend slice and ESLint clean (`.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:378-389`). | PASS |
| The implementation satisfies `#1376` without adding action-gating or validation behavior owned by later tasks | `#1377` task-local Architecture Review (2nd pass) marks this AC already satisfied (`.owlbear/kanban/tasks/1377-p2-02-implement-cockpit-task-detail-context-model.md:114`). Archived `#1376` builder notes record commit `216061a8` touching only `DetailTab.tsx` (`.owlbear/kanban/archive/1376-p2-01-test-cockpit-task-detail-context-model.md:128`), and the live `claimed` / `claimed_at` / `dep_status` usage is read-only display (`serve/cockpit/web/src/components/DetailTab.tsx:253-255`), not action gating. | PASS |

### Deductions
- `-0.03` quality-runner was not executed directly for this td:0/no-op review because the current scoped runner contract does not support a meaningful lint-only td:0 invocation; verdict relies on direct artifact inspection plus archived `#1376` runner evidence.
- `-0.02` the top-level `#1377` task framing is stale even though the latest task-local Architecture Review resolves it to a no-op.

### Confidence
- 0.95

### Verdict
- PASS
- Route: docs

### Action
- Advanced to docs.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder Notes: "Files changed: none." No-op pass-through task. No behavior, API, CLI, or config change. No IN-scope prose docs (READMEs, setup guides, share/README) reference the frontend task detail model. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Research doc (Section 2) uses only internal workspace sources and archived task records — no external repos, articles, or docs consulted. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1377-task-detail-context-model.md` exists (confirmed by file search) and is linked in the task body under `## Research`. Follow-up tasks listed in Section 5. |
| 5 | Diagram maintenance (describes match) | No | N/A | Changed-files set is empty ("Files changed: none"). `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**, serve/cockpit/web/src/**` but no files in that glob were changed by this task. No match. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1377-task-detail-context-model.md` | IN | Verified (exists, linked) |
| `serve/cockpit/web/src/components/DetailTab.tsx` | OUT (source) | N/A |
| `serve/cockpit/web/src/Shell.tsx` | OUT (source) | N/A |
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | OUT (source) | N/A |
| `serve/cockpit/src/owlbear_cockpit/view.py` | OUT (source) | N/A |
| `serve/kanban/src/owlbear_kanban/models.py` | OUT (source) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1377-*` files existed)
[[2026-05-08]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Frontend model matches backend fields for claim state | `TaskDetail` in DetailTab.tsx L16-31 has `claimed: boolean`, `claimed_at: string \| null`; backend `TaskSummary` exposes these and explicitly drops `claimed_by` (models.py L459-503) | PASS |
| Dependency/parent context preserved | `dep_status: string \| null`, `parent: number \| null`, `depends_on: number[]` in DetailTab.tsx L28-30; Shell.tsx L85-121 fetches into TaskDetail; mutation routes return SingleTaskResponse via model_dump() | PASS |
| Optional context has explicit state, not clearing edit | All nullable fields typed as `T \| null` (not `undefined`); claimed_at/dep_status rendered read-only (L253-255); never sent in edit payloads (L157-180); parent clearing is explicit null via parseParent() | PASS |
| Existing flows continue to work | vitest: 1109 passed, 0 failed; archived #1376 evidence: 63 passed scoped tests, ESLint clean | PASS |
| Satisfies #1376 without action-gating | claimed/claimed_at/dep_status usage is read-only display only (L253-255); #1376 archived with GREEN commit 216061a8 | PASS |

### Test Results
- vitest: 1109 passed, 0 failed, 0 skipped (full frontend suite)
- eslint: pre-existing warnings only (0 files changed)
- pytest: 2921 passed, 167 failed (all pre-existing, 0 files changed by this task)
- ruff: 29 pre-existing violations (0 introduced)

### Architect Quality: 3/5
Original Problem Evidence was factually incorrect (claimed fields were already present). Required 2 architecture review passes plus research to resolve to no-op. Pipeline self-corrected but overhead was notable. Not 2/5 because the review process did catch and correctly resolve the issue.

### Deduction Breakdown
- AC quality score <= 3: -0.03
- All 5 AC lines have specific evidence: no deduction
- Reviewer evidence section present and detailed (PASS at 0.95): no deduction
- Lint violations: pre-existing only (0 files changed): no deduction
- Full-suite failures not in task scope (0 files changed): no deduction

### Confidence: 0.97
### Action: archive