---
id: 1247
title: Filter/Search UX for Kanban Board
status: archived
priority: medium
created: 2026-05-01T04:32:36.348648+00:00
updated: 2026-05-01T12:45:17.571859+00:00
tags:
- type:config
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-05-01]]
## Planning
### Decomposition: Filter/Search UX for Kanban Board
- Tasks created: 9
- Dependency layers: 5 (linear TDD chain)
- Phases: 5 (filter logic → component → board integration → accessibility → integration verification)

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1248 | P1-01: RED — filterTasks unit tests | critical | — | phase-1, scope:cockpit-web, tdd:red |
| 1249 | P1-02: GREEN — filterTasks pure function + FilterState type | critical | 1248 | phase-1, scope:cockpit-web, tdd:green |
| 1250 | P2-01: RED — FilterPanel component tests | needed | 1249 | phase-2, scope:cockpit-web, tdd:red |
| 1251 | P2-02: GREEN — FilterPanel controlled component | needed | 1250 | phase-2, scope:cockpit-web, tdd:green |
| 1252 | P3-01: RED — KanbanBoard filter integration tests | needed | 1251 | phase-3, scope:cockpit-web, tdd:red |
| 1253 | P3-02: GREEN — KanbanBoard filter state and layout integration | needed | 1252 | phase-3, scope:cockpit-web, tdd:green |
| 1254 | P4-01: RED — Filter accessibility tests | important | 1253 | phase-4, scope:cockpit-web, tdd:red |
| 1255 | P4-02: GREEN — Filter accessibility implementation | important | 1254 | phase-4, scope:cockpit-web, tdd:green |
| 1256 | P5-01: Integration tests — full board filter flow | important | 1255 | phase-5, scope:cockpit-web, test:integration |

### Dependency Graph
```mermaid
graph LR
  1248[P1-01 RED filterTasks tests] --> 1249[P1-02 GREEN filterTasks impl]
  1249 --> 1250[P2-01 RED FilterPanel tests]
  1250 --> 1251[P2-02 GREEN FilterPanel impl]
  1251 --> 1252[P3-01 RED Board integration tests]
  1252 --> 1253[P3-02 GREEN Board integration]
  1253 --> 1254[P4-01 RED A11y tests]
  1254 --> 1255[P4-02 GREEN A11y impl]
  1255 --> 1256[P5-01 Integration verification]
```
[[2026-05-01]]
## Architecture Review — Decomposition Validation

### Verdict: APPROVE (decomposition parent advance)

Planner completed decomposition: 9 subtasks across 5 phases with linear TDD chain. Planning section present and structurally sound.

### Decomposition Assessment

| Criterion | Assessment |
|-----------|-----------|
| Phase granularity | PASS — 5 phases (pure logic → component → integration → a11y → verification) follow clean incremental layering |
| TDD pairing | PASS — RED/GREEN pairs for phases 1–4; phase 5 is verification-only |
| Dependency chain | PASS — linear chain is correct; each GREEN depends on preceding RED |
| Single responsibility | PASS — each task has one concern |
| Codebase alignment | PASS — Task interface has all needed fields (title, priority, tags, blocked); Board provides priorities list; PDS v4 exports PSelect, PMultiSelect, PSwitch |

### Issues for Subtask Reviews

1. **Path inconsistency:** #1249 AC says `lib/filterTasks.ts` but #1248 research says `../utils/filterTasks`. Codebase has `hooks/`, `components/`, `api/`, `__tests__/` — no `lib/` or `utils/`. Recommend `utils/filterTasks.ts` (more descriptive for non-hook pure functions). Fix in #1249 architect review.
2. **#1256 tagging:** Tagged `test:integration` but needs `type:test` pass-through tag for test-writer routing. Fix in #1256 architect review.
3. **Subtask pipeline status:** #1249–#1256 created in `research` — they have complete AC and will route through researcher before reaching architect. Normal pipeline flow; researchers may add useful codebase context.

### Codebase Evidence

- KanbanBoard.tsx: manages contextMenu, moveError, dragSourceStatus state — AC for #1252/#1253 correctly references these for filter interaction rules
- Task interface (useBoard.ts): `title: string`, `priority: string`, `tags: string[]`, `blocked: boolean` — all four filter dimensions present
- Board interface: `priorities: string[]` — available for priority dropdown
- PDS package verified: PSelect, PSelectOption, PMultiSelect, PMultiSelectOption, PSwitch all exported from @porsche-design-system/components-react ^4.0.0
- No existing filter/search code — this is greenfield

### Action

Tagged parent `type:config` for test-writer pass-through. Advanced to todo.
[[2026-05-01]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Parent decomposition task: 9 subtasks created across 5 TDD phases (#1248–#1256).
- Passing through to builder.
[[2026-05-01]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Tests: not applicable (decomposition/config pass-through task).
- Coverage: not applicable.
- ruff: not applicable.
- Passing through to review.
[[2026-05-01]]
## Review Evidence
### Review Scope
- Non-implementation parent/config task. Quality-runner confirmed tests, lint, and coverage are not applicable for an empty scoped run on this task.
- Task 1247 has no explicit `## Acceptance Criteria` section, so review anchored to the decomposition deliverable in `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md` plus the referenced filter/search brief and created child-task artifacts.

### Test Results
- quality-runner: N/A. `test_paths=[]` was respected for this decomposition/config task.
- Structured report: 0 passed, 0 failed, 0 skipped; status N/A.

### Lint
- quality-runner: N/A. `lint_paths=[]` was respected for this decomposition/config task.
- Structured report: clean=true; status N/A.

### Coverage
- N/A. No source modules or task-owned tests are in scope for task 1247.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. Parent config task has no `TestFromAC_*` classes, and both upstream notes marked tests not applicable.

#### Security Review
- No executable code changes are in scope. Builder notes explicitly state "no code changes needed" at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:92`.

#### Test Integrity
- N/A. No `TestFromAC_*` content exists on this parent task.

#### Test Quality
- N/A. No task-owned tests.

#### Data Safety
- No issues in scope. This task delivered task decomposition and metadata only.

#### Implementation-Aware Gaps
| Finding | Evidence | Status |
|---------|----------|--------|
| Child-task path contract drift | Parent architecture review records an unresolved inconsistency at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:70`. Child task 1249 still requires `lib/filterTasks.ts` at `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:24`. The governing brief also specifies `lib/filterTasks.ts` at `.owlbear/briefs/draft-filter-search-ux/brief.md:19`, `.owlbear/briefs/draft-filter-search-ux/brief.md:54`, and `.owlbear/briefs/draft-filter-search-ux/brief.md:234`. But the already-created RED suite imports `../utils/filterTasks` at `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts:19`, and the stub exists in `serve/cockpit/web/src/utils/filterTasks.ts:11`. The decomposition therefore hands downstream agents conflicting file targets. | FAIL |
| Child-task routing metadata defect | Parent architecture review records that child task 1256 needs a `type:test` pass-through tag at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:71`. The child task header currently includes only `test:integration` at `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:11`, and no `type:test` tag is present. This leaves the integration-test subtask misrouted. | FAIL |

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Structural positives verified: task file records 9 subtasks, 5 dependency layers, and 5 phases at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:22`, `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:23`, and `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:24`.
- Rejection is not about missing code or skipped tests. It is about unresolved decomposition defects in the child-task contracts.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Decompose the feature into a linear 5-phase TDD chain | Verified in `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:22`, `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:23`, and `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:24`. | N/A | PASS |
| Child-task contracts remain internally consistent with brief authority and adjacent phase artifacts | Conflicting file target across `.owlbear/briefs/draft-filter-search-ux/brief.md:19`, `.owlbear/briefs/draft-filter-search-ux/brief.md:54`, `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:24`, `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts:19`, `serve/cockpit/web/src/utils/filterTasks.ts:11`, and parent note `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:70`. | N/A | FAIL |
| Downstream test task routes correctly through the pipeline | Parent note `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:71` identifies the required `type:test` tag, but child header `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:11` still only carries `test:integration`. | N/A | FAIL |

### Confidence: .73
### Verdict: FAIL

### Required Follow-up
1. Correct the file-path contract across the brief and child tasks so phase 1 and phase 2 reference one authoritative `filterTasks` module path.
2. Add the missing `type:test` routing tag to task 1256.
3. Re-run review after the decomposition artifacts are internally consistent.

### Reflection
- Problem faced: the parent task has no explicit acceptance-criteria block, so the review had to ground itself in the decomposition artifact plus brief authority.
- Pattern discovered: parent decomposition reviews must verify child-task metadata and routing, not just task counts and dependency shape.
- Quality gap: architecture review documented both defects but still advanced the parent, which would push avoidable churn into downstream subtasks.
[[2026-05-01]]
## Architecture Review — Reviewer Rejection Resolution

### Context
Reviewer rejected #1247 (confidence .73) with two decomposition defects in child-task contracts. Both defects documented in prior architecture review but not corrected at that time. This review resolves them.

### Defect Resolution

| Defect | Reviewer Finding | Action Taken |
|--------|-----------------|--------------|
| Path contract drift | #1249 AC says `lib/filterTasks.ts`; RED suite (#1248) imports `../utils/filterTasks`; stub committed at `utils/filterTasks.ts` | Appended binding path correction to #1249 body: `lib/filterTasks.ts` → `utils/filterTasks.ts`. Authoritative path: `serve/cockpit/web/src/utils/filterTasks.ts` (committed stub + RED import). Downstream architect for #1249 will refine AC text to match. |
| Missing routing tag | #1256 tagged `test:integration` only; needs `type:test` for test-writer pass-through | Added `type:test` tag to #1256 via `edit_task`. Tag now present: `phase-5, scope:cockpit-web, test:integration, type:test`. |

### Brief vs Reality
The brief at `.owlbear/briefs/draft-filter-search-ux/brief.md` still references `lib/filterTasks.ts`. Brief is a design artifact superseded by implemented reality. Task AC (corrected) takes precedence for builders. No brief edit needed — it served its purpose during planning.

### Evaluation (re-review scope: decomposition consistency only)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Decomposition parent; no code |
| Interface clarity | PASS (after fix) | Path contract now consistent across #1248 (committed) and #1249 (corrected) |
| Dependency correctness | PASS | 9 subtasks, linear chain, all deps verified |
| Module layering | PASS | N/A for parent |
| TDD compliance | PASS | RED/GREEN pairs for phases 1-4; phase 5 is verification |
| KISS/YAGNI | PASS | Minimal decomposition for feature scope |
| Premise challenge | PASS | No existing filter code in codebase |
| Pattern consistency | PASS | Follows established task naming, tagging, and dependency conventions |
| Security surface | PASS | N/A for decomposition |
| Single domain | PASS | cockpit-web only |

### Test Depth
- Max depth: 0 (decomposition parent, no code)
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0 (decomposition parent)

### Verdict: APPROVE
### Action Taken: Fixed both reviewer-identified defects (path correction on #1249, routing tag on #1256). Re-approved decomposition parent. Advanced to todo.
[[2026-05-01]]
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable (second pass after review rejection fix).
- Decomposition defects resolved by architect: path contract corrected on #1249, `type:test` tag added to #1256.
- Subtask pipeline proceeds normally: #1248 already in-progress with 19 RED tests.
- Passing through to builder.
[[2026-05-01]]
## Builder Notes
- Scope: decomposition/config parent task only (`type:config`), no implementation files owned by this task.
- Files changed: none.
- Tests: N/A (quality-runner scoped run with empty `test_paths`). Result: 0 passed, 0 failed, 0 skipped.
- Coverage: N/A (no `coverage_modules` in scope).
- Lint: N/A (quality-runner scoped run with empty `lint_paths`).
- Evidence summary: Quality-runner confirmed this task is planning-only and all executable quality gates are not applicable; downstream quality validation belongs to child implementation tasks #1248–#1256.
- Fixes applied: none (no code surface in scope).
[[2026-05-01]]
## Review Evidence
### Review Scope
- Parent decomposition/config task (`type:config`) with no implementation files owned by this task.
- Max depth is td:0 per latest architecture refinement at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:198`; per review protocol this means quality-runner only and no code-reader fan-out.
- Task 1247 still has no explicit `## Acceptance Criteria` block, so this review is grounded in the planning artifact plus the latest architecture refinement after the prior rejection.

### Test Results
- quality-runner: N/A.
- Independent scoped run used `test_paths=[]` and confirmed empty scoped tests are treated as not applicable, not pass/fail.
- Structured result: 0 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: N/A.
- Independent scoped run used `lint_paths=[]` and confirmed empty lint scope is not applicable for this parent task.
- Structured result: clean execution, no files in scope.

### Coverage
- N/A. `coverage_modules=[]` and no implementation modules are owned by task 1247.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped correctly. No `TestFromAC_*` classes belong to this parent decomposition task.

#### Security Review
- No executable code changes are in scope. Latest builder notes state `no implementation files owned by this task` at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:214`.

#### Test Integrity
- N/A. Builder did not modify any `TestFromAC_*` content for this parent task.

#### Test Quality
- N/A. No task-owned tests.

#### Data Safety
- No issues in scope. This task owns planning/decomposition artifacts only.

#### Implementation-Aware Gaps
- No blocking gaps remain.
- Prior rejection defect 1 is fixed: child task 1249 now carries a binding path correction at `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:41` and `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:42`, aligning the downstream implementation target with the RED test import at `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts:19` and the committed stub in `serve/cockpit/web/src/utils/filterTasks.ts:11`.
- Prior rejection defect 2 is fixed: child task 1256 now includes both `test:integration` and `type:test` at `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:11` and `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:12`.
- The latest architecture refinement explicitly resolves brief/task authority: `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:180` states the stale brief path is superseded by implemented reality and the corrected task AC takes precedence.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Pass-through retry after reviewer rejection; no repeated ineffective implementation attempt |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Structural decomposition remains valid: 9 subtasks, 5 dependency layers, and 5 phases at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:22`, `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:23`, and `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:24`.
- Historical stale notes remain in the parent body, but the latest refinement after the rejection is explicit and internally consistent. This is not a current contract defect.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Decompose the feature into a linear 5-phase TDD chain | Planning artifact shows 9 subtasks across 5 dependency layers and 5 phases at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:22`, `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:23`, `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:24`. | N/A | PASS |
| Child-task contracts are internally consistent after the prior review rejection | 1249 correction note at `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:41` and `.owlbear/kanban/tasks/1249-p1-02-green-filtertasks-pure-function-filterstate-type.md:42`; aligned with RED import at `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts:19` and module stub at `serve/cockpit/web/src/utils/filterTasks.ts:11`. | N/A | PASS |
| Downstream test task routes correctly through the pipeline | 1256 tags now include both required entries at `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:11` and `.owlbear/kanban/tasks/1256-p5-01-integration-tests-full-board-filter-flow.md:12`. | N/A | PASS |
| Parent task correctly remains planning-only with executable quality gates marked N/A | Latest architecture review marks td:0 at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:198`; builder notes confirm no implementation scope at `.owlbear/kanban/tasks/1247-filter-search-ux-for-kanban-board.md:214`; quality-runner independently confirmed tests/lint/coverage are N/A for empty scoped inputs. | N/A | PASS |

### Deductions
- `0.04` deduction for having to ground the review in the planning artifact plus late architecture refinement rather than an explicit acceptance-criteria section.

### Confidence: .96
### Verdict: PASS
### Action
- Advanced to docs.

### Reflection
- Problem faced: the task body retains stale historical failure notes, so the review had to anchor on the latest refinement rather than earlier sections.
- Workaround applied: verified the live child-task files directly instead of trusting the re-approval summary.
- Pattern discovered: decomposition-parent reviews should treat appended post-rejection architecture refinements as the binding authority when they explicitly supersede stale brief/task text.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder notes: "Files changed: none." No behavior, API, CLI, config, or package structure changes owned by this task. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used — greenfield decomposition planning only. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this parent task. |
| 5 | Diagram maintenance (describes match) | No | N/A | `cockpit.excalidraw` describes `serve/cockpit/web/src/**`, but #1247 owns no changed files in that path. Referenced files (`filterTasks_1248.test.ts`, `utils/filterTasks.ts`) are child task #1248 artifacts, not owned by #1247. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| (none — builder confirmed "Files changed: none") | — | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1247-*` scratch files found)
[[2026-05-01]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decompose feature into linear 5-phase TDD chain | 9 subtasks, 5 phases, mermaid dependency graph in task body; all 9 child task files exist in kanban/tasks/ | PASS |
| Child-task contracts internally consistent | #1249 path correction note appended (utils/filterTasks.ts); RED import and stub align at serve/cockpit/web/src/utils/filterTasks.ts | PASS |
| Downstream test task routes correctly | #1256 tags confirmed: phase-5, scope:cockpit-web, test:integration, type:test | PASS |
| Parent remains planning-only with N/A quality gates | No code changes; builder/test-writer both noted N/A; quality-runner confirmed empty scope | PASS |

### Test Results
- pytest (full suite, no-cov): 1541 passed, 53 failed, 4 skipped
- All 53 failures are pre-existing debt in tasks #1196, #1199, #1176; none in #1247 scope
- ruff (full): 4 violations in knowledge, mcp-knowledge, mcp-memory, orchestrator; none in scope

### Reviewer Evidence
Present and thorough. Two-pass pipeline: first review correctly caught two decomposition defects (confidence .73 FAIL), second review confirmed fixes (confidence .96 PASS). Reviewer work was high quality.

### Architect Quality: 3/5
Decomposition structure is clean (9 tasks, 5 phases, linear TDD chain). However, two defects (path drift, missing routing tag) were documented in the architecture review but not corrected before advancing, causing a reviewer rejection and full pipeline re-cycle. No explicit AC section on the parent task forced reviewer to synthesize AC from the planning artifact.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC lines with no evidence | 0 (all 4 have evidence) |
| Lint violations in scope | 0 |
| AC quality score 3 (lte 3) | -0.03 |
| Missing reviewer evidence | 0 |
| Test failures in scope | 0 |

### Confidence: .97
### Action: archive