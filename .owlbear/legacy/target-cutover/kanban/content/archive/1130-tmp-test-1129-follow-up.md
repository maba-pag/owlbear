---
id: 1130
title: Implement cockpit mutation OCC parity (move/edit/release)
status: archived
priority: medium
created: 2026-04-26T15:37:49.084530+00:00
updated: 2026-04-27T03:51:34.817444+00:00
tags:
- cockpit
- research
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Research TOCTOU windows in Cockpit mutation endpoints and decompose remediation into atomic implementation tasks.

Acceptance Criteria:
- [x] Research doc produced at .owlbear/research/cockpit-mutation-occ-parity.md documenting TOCTOU gaps per endpoint
- [x] Remediation option selected: CockpitView facade (Option A) + engine release CAS (C1), confidence 0.82
- [x] Implementation decomposed into #1133 (engine release CAS) and #1132 (route wiring)
- [x] Dependency graph established: #1130 → #1133 → #1132 (serialized by shared mutation.py ownership)
- [x] Child task AC re-scoped for clean file ownership: #1133 = engine layer only, #1132 = route layer only

Likely files:
- .owlbear/research/cockpit-mutation-occ-parity.md

[[2026-04-26]]
## Research
- Research doc: .owlbear/research/cockpit-mutation-occ-parity.md
- Sources: 8 studied (all codebase-internal), 4 high-relevance
- Recommendation: Route through CockpitView facade + add expected_updated to engine.release_task (confidence: 0.82)
- Follow-up tasks created: #1132 (wire routes through CockpitView), #1133 (engine release CAS)
- Decision requests: none (T1 — refactor using existing facade)

## Key Findings
1. Routes call raw KanbanEngine directly, bypassing the OCC-aware CockpitView facade that already exists and is tested (#1078).
2. POST /edit has a route-level stale check but does NOT pass expected_updated to the engine write — TOCTOU gap between check and write.
3. POST /move has no OCC at all — MoveRequest lacks an updated field.
4. POST /release is LWW at every layer — engine.release_task has no expected_updated param.
5. ConcurrencyError(ERR_STALE) exists in the engine but is never caught/mapped to 409 in mutation routes.
[[2026-04-26]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Refined to research deliverable. Implementation split into #1133 (engine) + #1132 (routes) with clean file ownership |
| Interface clarity | PASS | AC is fully checked — research doc, option selection, decomposition, dependency graph |
| Dependency correctness | PASS | No deps (root task). Children: #1133 depends on #1130, #1132 depends on #1130 + #1133 |
| Module layering | PASS | Research task — no code changes. Child tasks respect engine → cockpit layering |
| TDD compliance | PASS | Tagged `research` — non-implementation pass-through |
| KISS/YAGNI | PASS | Minimal decomposition: 2 tasks covering engine CAS + route wiring |
| Premise challenge | PASS | TOCTOU gaps confirmed by code reading: mutation.py bypasses CockpitView, edit has precheck-only OCC, move has none, release is LWW |
| Pattern consistency | PASS | CockpitView facade already exists and is tested (#1078). Recommendation follows existing OCC pattern |
| Security surface | PASS | OCC fixes concurrency vulnerability (stale snapshot race). No new external inputs |
| Single domain | PASS | Refined to research. Child tasks scoped to single domains: #1133=kanban-engine, #1132=cockpit-routes |

### Architecture Notes
- **Original task had implementation AC duplicating child tasks.** Refined to research deliverable with all AC checked.
- **Child task overlap fixed.** Original #1133 included route changes (mutation.py, cockpit tests) overlapping with #1132. Re-scoped: #1133 = engine.py + CockpitView class only; #1132 = all route/DI/test changes. Serialized via #1132 depends_on #1133 (shared mutation.py ownership).
- **valid_transitions coupling:** Move route uses `adapter.valid_transitions(engine, ...)` which delegates to `KanbanEngine.valid_transitions()`. CockpitView doesn't expose this. AC on #1132 explicitly notes builder must either keep adapter call with engine access or rely on engine's ValueError (caught by CockpitView).
- **Test blast radius:** Existing move tests post no OCC token; release tests post no body. #1132 AC requires updating existing tests.
- **Status change on child tasks:** `edit_task(status=...)` errored (server bug). #1133 and #1132 remain at `research` — need manual move to `backlog` for their own arch review.

### Challenge Results
- Challenger: reconsider (0.63)
- Key concerns: (1) task-boundary overlap between #1132/#1133 on mutation.py, (2) weak DI dependency rationale, (3) AC ownership drift when refining to research
- Architect response: accepted all three. Re-scoped child tasks to eliminate file overlap (engine-only vs route-only). Revised dependency rationale to shared file ownership. Rewrote #1130 AC to research deliverable with explicit ownership handoff to child tasks.

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined #1130 AC to research deliverable, tagged `research`. Re-scoped #1133 (engine-only) and #1132 (routes-only) to eliminate file overlap. Set parent=1130 on both. Added #1133 as dependency of #1132. Child tasks need move from research → backlog (edit_task status bug blocked this).
[[2026-04-26]]
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.
[[2026-04-26]]
## Builder Notes
- Non-implementation task (tagged `research`) confirmed from `## Test-Writer Notes`.
- No code changes required in GREEN phase.
- Passing through to review.
[[2026-04-26]]
## Review Evidence
### Test Results
- N/A — tagged `research`; no implementation artifacts or task-scoped tests were produced in this task.
- Quality-Runner not invoked: this review is on research/task decomposition accuracy, not executable changes.

### Lint
- N/A — research deliverable only.

### Coverage
- N/A — research deliverable only.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — non-implementation task; no `TestFromAC_*` scope for this review.

#### Security Review
- No executable change under review.

#### Test Integrity
- N/A — no task-scoped tests were changed in this task.

#### Test Quality
- N/A — no task-scoped tests were authored in this task.

#### Research Artifact Accuracy
- Violation: the research doc misstates the live `move` route. `.owlbear/research/cockpit-mutation-occ-parity.md:31` says `POST /move` has no `updated` field and no `expected_updated` write path. Live code already defines `MoveRequest.updated` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:28-34`, performs a stale-snapshot precheck at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:94`, and passes `expected_updated=req.updated` to `engine.move_task()` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:108-109`.
- The same stale claim is echoed in the task body at `.owlbear/kanban/tasks/1130-tmp-test-1129-follow-up.md:43` and in the architecture verdict summary at `.owlbear/kanban/tasks/1130-tmp-test-1129-follow-up.md:58`.

#### Data Safety
- No new runtime data-safety issue introduced by this task itself.

#### Implementation-Aware Gaps
- The edit/release findings remain grounded in live code: edit still does a route-level stale precheck at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:211` and then calls `engine.edit_task(...)` without passing `expected_updated` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:221`.
- Release still has no OCC token at the route layer (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:228-242`) and engine release still writes last-writer-wins via `write_task(...)` at `serve/kanban/src/owlbear_kanban/engine.py:1266-1301`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc produced at `.owlbear/research/cockpit-mutation-occ-parity.md` documenting TOCTOU gaps per endpoint | File exists, but the `POST /move` row is factually stale at `.owlbear/research/cockpit-mutation-occ-parity.md:31` versus live route code at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:28-34` and `:108-109`. | FAIL |
| Remediation option selected: CockpitView facade (Option A) + engine release CAS (C1), confidence 0.82 | Recommendation is recorded at `.owlbear/research/cockpit-mutation-occ-parity.md:63`, but it is grounded on the stale premise above and still proposes adding `updated` to `MoveRequest` at `.owlbear/research/cockpit-mutation-occ-parity.md:69`, which already exists in live code. | FAIL |
| Implementation decomposed into #1133 (engine release CAS) and #1132 (route wiring) | Tasks exist, but `#1132` still instructs adding move OCC wiring at `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:24`, duplicating behavior already present in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:28-34` and `:108-109`. | FAIL |
| Dependency graph established: #1130 → #1133 → #1132 | Dependency chain is present at `.owlbear/kanban/tasks/1133-add-expected-updated-cas-param-to-engine-release-task.md:10-12` and `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:10-13`. | PASS |
| Child task AC re-scoped for clean file ownership: #1133 = engine layer only, #1132 = route layer only | Scope boundaries are clean at `.owlbear/kanban/tasks/1133-add-expected-updated-cas-param-to-engine-release-task.md:30` and `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:37`. | PASS |

### Deductions
- -0.18 factual substrate drift: research doc claims a `move` TOCTOU gap that current code has already closed.
- -0.10 downstream task drift: `#1132` duplicates already-implemented `move` OCC work.
- -0.04 recommendation confidence overstated from a stale premise.

### Verdict
- FAIL -> backlog | confidence 0.68

### Action
- Refresh the research doc and `#1132` against the live `mutation.py` substrate before re-entering the pipeline.
- Preserve the still-grounded edit/release OCC findings and the clean engine-vs-route ownership split, but remove or narrow the already-satisfied `move` work.
[[2026-04-26]]
## Errata (Reviewer Cycle 1 + Architect Cycle 2)

**Stale move finding corrected:** Key Finding 3 ("POST /move has no OCC at all") and Key Finding 4 ("ConcurrencyError(ERR_STALE) is never caught/mapped to 409") are factually stale for the move endpoint. Live `mutation.py` already has:
- `MoveRequest.updated` (L29-34) — OCC token required
- Stale-snapshot precheck (L94) — 409 on mismatch
- `expected_updated=req.updated` pass-through to engine (L108-109)
- `ConcurrencyError` → 409 mapping (L110-113)

**Still-valid findings:** Edit TOCTOU (route prechecks but `_build_edit_kwargs` strips `updated` at L121, so `expected_updated` never reaches engine) and release LWW (no OCC at any layer) remain confirmed against live code.

**Research doc not corrected:** `.owlbear/research/cockpit-mutation-occ-parity.md` retains the stale move analysis. Builders of #1132/#1133 must use this errata and the corrected #1132 AC, not the research doc's move endpoint row.

**Dependency rationale updated:** #1130 → #1133 → #1132 serialization is because #1133 adds `expected_updated` to engine `release_task` which #1132's route layer needs. The "shared mutation.py ownership" rationale from cycle 1 is outdated — file ownership is now cleanly split (engine-only vs route-only).

**Child task status:** `edit_task(status=backlog)` errors with server bug. #1132 and #1133 remain at `research`; need manual move to `backlog`.
[[2026-04-26]]
## Architecture Review (Cycle 2)

### Context
Returning from reviewer FAIL (confidence 0.68). Reviewer found the research doc's POST /move TOCTOU claim is stale — live code already has full move OCC. Edit and release findings remain valid.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research deliverable only. Implementation split into #1133 (engine) + #1132 (routes) |
| Interface clarity | PASS | AC fully checked; errata documents stale move finding with line-level evidence |
| Dependency correctness | PASS | #1130 → #1133 → #1132. Rationale: #1133 adds engine CAS that #1132 routes need |
| Module layering | PASS | Research task — no code changes. Child tasks respect engine → cockpit layering |
| TDD compliance | PASS | Tagged `research` — non-implementation pass-through |
| KISS/YAGNI | PASS | Minimal decomposition: 2 child tasks for remaining edit/release gaps |
| Premise challenge | PASS | Move finding stale but corrected via errata. Edit TOCTOU (L211 precheck, L121 strips updated, L221 no pass-through) and release LWW (L228-242) confirmed against live code |
| Pattern consistency | PASS | CockpitView facade routing follows existing #1078 pattern |
| Security surface | PASS | OCC fixes concurrency vulnerability. No new external inputs |
| Single domain | PASS | Research task. Child tasks single-domain: #1133=kanban-engine, #1132=cockpit-routes |

### Challenge Results
- Challenger: reconsider (0.44)
- Key concerns: (1) parent body had stale key findings, (2) research doc not corrected, (3) child task status move failed, (4) dependency rationale drift
- Architect response: accepted all four. (1) Added errata section to parent body with line-level corrections. (2) Research doc correction is outside architect's editable surface — errata directs builders to use corrected #1132 AC, not research doc move row. (3) Documented server bug; child tasks need manual move from research → backlog. (4) Updated rationale: serialization is because #1133 adds engine API that #1132 routes consume, not shared file ownership.

### Residual Risk
- Research doc `.owlbear/research/cockpit-mutation-occ-parity.md` still contains stale move analysis. Builders MUST use #1132 errata and corrected AC. Low risk: #1132 AC is the authoritative build spec, not the research doc.
- Child tasks #1132/#1133 stuck at `research` due to `edit_task(status=...)` server bug. **Manual action needed: move both to `backlog`.**

### Verdict: APPROVE (after REFINE)
### Action Taken: Added errata to #1130 correcting stale move findings. Rewrote #1132 AC to remove stale move OCC claims and clarify CockpitView routing for move is pattern-consistency (not OCC fix). Updated dependency rationale. Child tasks need manual move to backlog.
[[2026-04-26]]
## Test-Writer Notes
- Retry cycle: reviewer cited research artifact accuracy (stale move TOCTOU claim), not missing tests.
- Task tagged `research` — no testable Python interfaces.
- Passing through to builder to apply errata corrections to research doc and #1132 AC.
[[2026-04-26]]
## Builder Notes
- Non-implementation research task; applied errata corrections requested by `## Test-Writer Notes` to task-owned artifacts.
- Updated `.owlbear/research/cockpit-mutation-occ-parity.md` to reflect live move OCC parity (move already uses OCC token + expected_updated + stale conflict mapping) while preserving validated edit/release gaps.
- Aligned #1132 task reference line with corrected research framing (move routing remains for CockpitView consistency, not as an OCC fix).
- Tests: N/A (no Python runtime changes in this task).
- Lint: N/A (markdown/task-artifact update only).
- Evidence summary: stale move claims removed from the research analysis and recommendation sections; recommendation now targets edit/release OCC parity and release CAS additions.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner: 0 passed, 0 failed, 0 skipped.
- Exit codes: pytest 5 (no tests collected), ruff 0.
- Scope note: empty scoped run is valid here. Task 1130 is a research/markdown-only retry with no runnable code or test targets.

### Lint
- Clean for empty scope; no executable paths applicable.

### Coverage
- N/A for a research/markdown-only task.

### Review Scope
- Directly verified the task-owned artifacts named by the builder: `.owlbear/research/cockpit-mutation-occ-parity.md`, `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md`, and the parent task body.
- Cross-checked those artifacts against live code in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` and `serve/kanban/src/owlbear_kanban/engine.py`.
- Source-control changed-files view was unavailable in the current toolset, so retry scope was corroborated from builder notes plus direct reads of the named artifacts.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — no `TestFromAC_*` scope for this research task, and quality-runner confirmed no runnable targets.

#### Security Review
- No executable change under review.
- The research artifact still accurately describes the live edit and release concurrency gaps at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:211`, `:221`, `:228`, `:237` and `serve/kanban/src/owlbear_kanban/engine.py:1271`, `:1298`, `:1306`.

#### Test Integrity
- N/A — no task-scoped tests changed.

#### Test Quality
- N/A — no task-scoped tests authored.

#### Data Safety
- No new data-safety issue introduced by the reviewed artifacts.

#### Implementation-Aware Gaps
- None in the active research deliverable after the retry. The move endpoint is now documented as already OCC-complete, while edit and release remain correctly identified as gaps.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Prior Review Evidence sections | 1 |
| Approach variation | Yes — the retry corrected task-owned research/task artifacts after the first review failure |
| Assessment | CLEAN |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc produced at `.owlbear/research/cockpit-mutation-occ-parity.md` documenting TOCTOU gaps per endpoint | `.owlbear/research/cockpit-mutation-occ-parity.md:31` now records `POST /move` as OCC-complete; live route code matches at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34`, `:94`, `:109`, and `:111`. The remaining edit and release gaps described in the doc match live code at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:211`, `:221`, `:228`, `:237` and `serve/kanban/src/owlbear_kanban/engine.py:1271`, `:1298`, `:1306`. | PASS |
| Remediation option selected: CockpitView facade (Option A) + engine release CAS (C1), confidence 0.82 | `.owlbear/research/cockpit-mutation-occ-parity.md:63` records the selected option and confidence. The follow-on route plan keeps move OCC-equivalent routing for consistency at `.owlbear/research/cockpit-mutation-occ-parity.md:69-70`. | PASS |
| Implementation decomposed into #1133 (engine release CAS) and #1132 (route wiring) | Child tasks exist at `.owlbear/kanban/tasks/1133-add-expected-updated-cas-param-to-engine-release-task.md` and `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md`. The corrected route-task errata is at `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:23`, and its move-routing AC is narrowed to pattern consistency at `:29`. | PASS |
| Dependency graph established: #1130, #1133, #1132 | `#1133` depends on `#1130` at `.owlbear/kanban/tasks/1133-add-expected-updated-cas-param-to-engine-release-task.md:12`. `#1132` depends on both `#1130` and `#1133` at `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:12-13`. | PASS |
| Child task AC re-scoped for clean file ownership: #1133 = engine layer only, #1132 = route layer only | Engine-only scope is explicit at `.owlbear/kanban/tasks/1133-add-expected-updated-cas-param-to-engine-release-task.md:30`; route-only scope is explicit at `.owlbear/kanban/tasks/1132-wire-cockpit-mutation-routes-through-cockpitview-facade.md:38`. | PASS |

### Pass 2 — INFORMATIONAL
- Historical first-cycle prose in the parent task body is still stale at `.owlbear/kanban/tasks/1130-tmp-test-1129-follow-up.md:26`, `:43`, and `:65`, but the binding corrections are explicit later in the same task at `:152`, `:162`, and `:194-195`.
- Child tasks `#1132` and `#1133` remain in `research` because `edit_task(status=...)` errored during architecture review; this is an operational follow-through issue, not a failure of this task's research AC.

### Deductions
- -0.03 conflicting historical prose remains in earlier sections of the parent task body, even though later errata and architecture sections supersede it.
- -0.02 no direct source-control changed-files view was available in the current toolset; retry scope was reconstructed from named artifacts and direct reads.

### Verdict
- PASS to docs with confidence .93

### Action
- Research artifact and child-task decomposition are now aligned with live move/edit/release behavior.
- Remaining operational note: child tasks `#1132` and `#1133` still need manual movement from `research` to `backlog` because of the status-change server bug documented in the parent task.
[[2026-04-27]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Research-only task; no README or setup-guide references cockpit mutation OCC behavior |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | All 8 sources codebase-internal (per builder notes) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/cockpit-mutation-occ-parity.md` exists, linked from task body; move row corrected per errata; follow-up tasks #1132 and #1133 created |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: .owlbear/**` — matches the changed research doc. Footer updated to `Last verified: 2026-04-27 (cfa0facd)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/cockpit-mutation-occ-parity.md` | IN | Verified |
| `.owlbear/kanban/tasks/1130-*.md` | OUT (kanban task file) | N/A |
| `.owlbear/kanban/tasks/1132-*.md` | OUT (kanban task file) | N/A |
| `.owlbear/kanban/tasks/1133-*.md` | OUT (kanban task file) | N/A |
| `share/diagrams/project-overview.excalidraw` | IN (diagram) | Updated footer |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer bumped to `2026-04-27 (cfa0facd)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/1130-*` files existed)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at `.owlbear/research/cockpit-mutation-occ-parity.md` documenting TOCTOU gaps per endpoint | File exists; move row corrected to OCC-complete at `:31`; edit/release gaps verified against live `mutation.py:211,:221,:228,:237` and `engine.py:1271,:1298,:1306` | PASS |
| Remediation option selected: CockpitView facade (Option A) + engine release CAS (C1), confidence 0.82 | Recorded at `:63`; recommendation now correctly scoped to edit/release OCC + move pattern consistency | PASS |
| Implementation decomposed into #1133 (engine release CAS) and #1132 (route wiring) | Tasks exist with proper AC; both reference research doc; #1132 errata corrects stale move claims | PASS |
| Dependency graph established: #1130 → #1133 → #1132 | Verified in task metadata: #1133 depends_on=[1130], #1132 depends_on=[1130,1133] | PASS |
| Child task AC re-scoped for clean file ownership: #1133 = engine layer only, #1132 = route layer only | Scope boundaries explicit: #1133 at `:30` (engine.py + CockpitView), #1132 at `:38` (mutation.py, deps.py, models.py, cockpit tests) | PASS |

### Test Results
- pytest: 2272 passed, 166 failed, 4 skipped (exit 1). Failures from systemic `ConfigError: agent_map missing status entries` in board fixtures — unrelated to this research/markdown-only task.
- ruff: 8 violations in knowledge/mcp-knowledge/mcp-memory/orchestrator packages — outside task scope.

### Architect Quality: 4/5
AC structure was specific and verifiable. The stale move finding in initial research caused a full review-reject cycle, but the AC itself guided precise verification. Architect corrected cleanly via errata in cycle 2.

### Deduction Breakdown
- AC lines: all 5 with specific evidence → no deduction
- Lint: violations outside task scope → no deduction
- AC quality 4/5 (>3) → no deduction
- Reviewer evidence: present, thorough, PASS at .93 → no deduction
- Full suite failures: systemic ConfigError, not task-caused → no deduction
- Uncommitted builder corrections found and committed → -0.01

### Confidence: 0.99
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b54ebc43 | docs(research) | cockpit-mutation-occ-parity.md | #1130 |
| 08e62913 | docs(research) | cockpit-mutation-occ-parity.md, 1130-*.md | #1130 |