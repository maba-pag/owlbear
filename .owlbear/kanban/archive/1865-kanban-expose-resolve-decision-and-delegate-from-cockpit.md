---
id: 1865
title: 'Kanban: expose resolve_decision() and delegate from Cockpit'
status: archived
priority: important
created: 2026-05-25T00:06:59.303292+02:00
updated: 2026-05-25T06:50:10.290014+02:00
tags:
  - scope:kanban
  - scope:cockpit-backend
  - boundary-audit
  - quality
parent:
depends_on:
  - 1868
  - 1869
ac:
  - 'Children #1868 and #1869 both reach status done or archived — verifiable via
    show_task for each'
  - tests/test_cockpit_decisions_api.py full test suite passes after both 
    children merge — confirms end-to-end decision resolution flow (frontmatter 
    persistence, response-section append, file move, unblock, duplicate 
    handling) works through the refactored kanban.decisions.resolve_decision() 
    path
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Parent/umbrella task — decomposed into implementation children.

Scope: Extract decision resolution lifecycle from Cockpit into `owlbear_kanban.decisions.resolve_decision()`, then delegate from Cockpit route.

Ref: .owlbear/research/cockpit-api-boundary-audit.md — Finding 1
Research: .owlbear/research/1865-resolve-decision-extraction.md

## Decomposition
- #1868 — Kanban: add `resolve_decision()` to decisions module + unit tests
- #1869 — Cockpit: delegate decision resolution to kanban (depends on #1868)

## Architecture Notes for Children
- **FileNotFoundError contract (#1868):** Current Cockpit endpoint swallows `FileNotFoundError` from `engine.edit_task()` (legacy callers may resolve DRs pointing to tasks outside this engine). The new `resolve_decision()` must preserve this behavior — swallow internally, do NOT propagate. Architect reviewing #1868 must ensure AC reflects this.
- **Consolidation test backstop:** Existing `tests/test_cockpit_decisions_api.py` tests the full resolve flow end-to-end (frontmatter persistence, response-section append, file move, unblock, duplicate handling). These serve as the natural consolidation backstop after refactor — no separate consolidation-test task needed.
- **Helpers to move:** `_append_response_section` and `_rewrite_response` from Cockpit route become internal to `resolve_decision()` in kanban module.

[[2026-05-25T00:43:27+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent is umbrella only; children each have single domain |
| Interface clarity | PASS | Children define clear entry points (resolve_decision function, route delegation) |
| Dependency correctness | PASS | #1869 depends_on #1868 — correct build order |
| Module layering | PASS | kanban.decisions (domain) ← cockpit.routes (HTTP layer) — correct direction |
| TDD compliance | N/A | Non-impl umbrella task |
| KISS/YAGNI | PASS | Minimal 2-task decomposition, no extra abstractions |
| Premise challenge | PASS | Boundary audit identified real leak; existing patterns (create_dr symmetry) confirm need |
| Pattern consistency | PASS | Symmetric with create_dr(); follows DecisionEngine protocol |
| Security surface | PASS | Internal refactor, no new boundaries |
| Single domain | PASS | Parent acknowledged multi-domain; decomposed into single-domain children |

### Architecture Notes
- FileNotFoundError contract flagged for #1868 review: current behavior swallows it, new function must preserve this
- Existing test_cockpit_decisions_api.py serves as consolidation backstop — no separate task needed
- Helpers _append_response_section and _rewrite_response move into kanban module internals

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: scope-state mismatch (body not umbrella-clean), FileNotFoundError contract drift, AC not persisted
- Architect response: accepted and addressed — rewrote body to umbrella form, persisted AC, flagged FileNotFoundError for #1868 review, confirmed consolidation backstop exists

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP (bundle skip)

### Verdict: APPROVE (REFINE → APPROVE)
### Action Taken: Rewrote body to umbrella form, added verifiable AC, tagged quality (pass-through), set proof_bundle=skip, advanced to todo

[[2026-05-25T00:50:59+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Also tagged `quality` (non-implementation umbrella task).
- Passing through to builder.

[[2026-05-25T01:06:18+02:00]]
## Builder Notes
- Implementation: none (umbrella/pass-through task)
- Tests: not applicable for parent decomposition task (proof bundle: skip)
- Coverage: not applicable
- ruff: not applicable
- Approach: verified AC against child tasks only. Evidence: #1868 has parent=1865 with scope:kanban tag; #1869 has parent=1865 with scope:cockpit-backend tag and depends_on=[1868]. No code changes required.
- Evidence summary: AC satisfied by existing decomposition and dependency topology; advanced per proof-bundle skip flow.

[[2026-05-25T01:19:21+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC lines 1-3 / parent closure contract | The parent AC set proves only decomposition metadata, but the task scope still describes feature delivery (extract `resolve_decision()` into kanban and delegate from Cockpit). Both named implementation children remain open, so the umbrella task can false-green in review without the feature being delivered. | 1865:30, 1865:35-37, 1865:92; 1868:4, 1868:11; 1869:4, 1869:11-13 | backlog |
| 2 | Proof sufficiency | Builder evidence relied on `proof_bundle: skip` and topology-only verification, while the parent task itself names a feature-level consolidation backstop for the full decision-resolve flow. No such feature-level proof exists yet because the delegated implementation tasks are not complete. | 1865:21, 1865:41, 1865:92; 1868:4; 1869:4 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite the parent task so its closure criteria match its role: either make it an explicit decomposition-only coordination task or require both child implementations to complete and the named consolidation proof to exist before the task can return to review. | .owlbear/kanban/tasks/1865-kanban-expose-resolve-decision-and-delegate-from-cockpit.md | Parent scope/evidence mismatch at 1865:30, 1865:35-37, 1865:41, 1865:92 with child statuses at 1868:4 and 1869:4 |
| 2 | architect | Keep the umbrella task out of review until the exact delegated child set (#1868, #1869) is finished and routed with feature-level proof rather than metadata-only pass-through evidence. | .owlbear/kanban/tasks/1865-kanban-expose-resolve-decision-and-delegate-from-cockpit.md, .owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md, .owlbear/kanban/tasks/1869-cockpit-delegate-decision-resolution-to-kanban-resolve-decision.md | 1865:35-37, 1865:92, 1868:4, 1869:4 |

## Observations
- The decomposition itself is coherent: the parent explicitly names exactly two children, `#1868` and `#1869`, and their scope tags/dependency chain match the frontmatter constraints in AC lines 1-3.
- I did not dispatch `quality-runner` because this failure is at the parent-task contract/routing layer, not at an implementation or scoped-test evidence layer.

[[2026-05-25T01:36:44+02:00]]
## Architecture Review (Revision 2 — Post-Reject)
### Reviewer Findings Addressed
| # | Finding | Fix Applied |
|---|---------|-------------|
| 1 | AC proved only decomposition topology; could false-green before children deliver | Rewrote AC to gate on child status (done/archived) + consolidation test |
| 2 | proof_bundle=skip allowed metadata-only pass-through; consolidation backstop not enforced | Escalated to proof_bundle=existing; named tests/test_cockpit_decisions_api.py as proof scope |

### Changes Made
- **AC rewritten:** 2 lines — (1) both children reach done/archived, (2) consolidation test passes through refactored path
- **depends_on: [1868, 1869]** added — dep-blocks the parent until both children complete their pipeline cycles
- **proof_bundle: existing** — reviewer must verify named consolidation test suite; test-writer still SKIP (quality tag)
- **quality tag retained** — test-writer and builder pass through; reviewer is the verification gate

### Proof-Bundle Validation
- Previous assignment: skip (architect cycle 1)
- Final bundle: existing
- Existing proof scope: tests/test_cockpit_decisions_api.py
- Test-writer: SKIP (bundle existing + quality tag)

### Challenge Results
- Challenger: SKIPPED — proof bundle `existing` (per Step 2.1 gating)

### Closure Contract
The dep-block on [1868, 1869] prevents this task from advancing until both implementation children complete. When unblocked, the pipeline flow is:
- Test-writer: SKIP (quality + existing bundle)
- Builder: pass-through (quality tag) — verifies children done, runs consolidation test
- Reviewer: verifies AC (child statuses + test evidence) against existing proof scope

### Verdict: APPROVE (REFINE → APPROVE)
### Action Taken: Rewrote AC to feature-closure criteria, added depends_on [1868, 1869], escalated proof_bundle to existing, re-advanced to todo

[[2026-05-25T06:01:50+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Tagged `quality` (non-implementation umbrella task).
- Existing proof scope: tests/test_cockpit_decisions_api.py
- Passing through to builder.

[[2026-05-25T06:13:21+02:00]]
## Builder Notes
- Implementation: none (umbrella quality/pass-through task)
- Files changed: none
- AC verification:
  - AC1 (children complete): verified via `show_task` that #1868 status=archived and #1869 status=archived.
  - AC2 (existing proof): ran quality-runner scoped proof on `tests/test_cockpit_decisions_api.py`.
- Test results (quality-runner): 89 passed, 0 failed, 0 skipped.
- Lint status (quality-runner): clean=true, no violations.
- Coverage: not requested by proof bundle `existing` and not required by AC.
- Evidence summary: Parent closure criteria satisfied with child completion plus green consolidation backstop; task advanced to review.

[[2026-05-25T06:26:56+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1865 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first and remained internally consistent. The parent builder note reports AC1 child-status verification and a quality-runner scoped proof on `tests/test_cockpit_decisions_api.py` with 89 passed, 0 failed, 0 skipped, plus clean lint.
- AC evidence map:

| AC | Code Evidence | Test/Task Evidence | Status |
|---|---|---|---|
| 1 | `.owlbear/kanban/archive/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md:4` and `:11` plus `.owlbear/kanban/archive/1869-cockpit-delegate-decision-resolution-to-kanban-resolve-decision.md:4` and `:11` show both delegated children are archived under parent `1865`. | Parent builder verification at `.owlbear/kanban/tasks/1865-kanban-expose-resolve-decision-and-delegate-from-cockpit.md:161-162` matches the authoritative child task state returned by `show_task`. | PASS |
| 2 | `serve/kanban/src/owlbear_kanban/decisions.py:187` defines `resolve_decision()`, and `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:170` delegates the Cockpit resolve endpoint through `kanban_resolve_decision(...)`, so the end-to-end route now runs through the extracted kanban path. | Parent builder proof at `.owlbear/kanban/tasks/1865-kanban-expose-resolve-decision-and-delegate-from-cockpit.md:162-164` reports the named suite green. The existing suite directly covers frontmatter persistence at `tests/test_cockpit_decisions_api.py:958`, response-section append/order at `tests/test_cockpit_decisions_api.py:975` and `:1011`, file move at `tests/test_cockpit_decisions_api.py:1177`, unblock at `tests/test_cockpit_decisions_api.py:1206` and `:1541`, and duplicate handling at `tests/test_cockpit_decisions_api.py:1487`. | PASS |

## Observations
- The architecture rewrite on the parent task fixed the earlier false-green risk: closure now depends on the exact delegated child set and a named consolidation suite rather than topology-only metadata.
- I did not dispatch `quality-runner` independently because the builder proof packet was sufficient for an `existing` bundle and direct file inspection of the delegated code path and cited tests found no contradiction.

[[2026-05-25T06:38:51+02:00]]
## Docs Gate

**Verdict: PASS — no documentation updates required.**

### Changed files (from children #1868, #1869)
- `serve/kanban/src/owlbear_kanban/decisions.py` — added `resolve_decision()` standalone function
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` — delegates to `kanban_resolve_decision()`

### Item 1: README Verification
- **`serve/kanban/README.md`**: `resolve_decision()` is not in `owlbear_kanban.__init__` and is not part of the top-level namespace. Convention check: no other standalone decisions functions (`create_dr`, `parse_dr`, `move_to_resolved`, `resolve_pending_drs`) are documented either — adding `resolve_decision` follows the same pattern. No contradiction introduced. No action needed.
- **`serve/cockpit/README.md`**: `POST /api/decisions/{id}/resolve` behavior description (line 621) remains accurate — endpoint behavior unchanged; internal helpers `_append_response_section`/`_rewrite_response` were never documented. No contradiction.

### Item 2: External Attribution
N/A — internal refactoring, no external sources.

### Item 3: Research Doc
N/A check satisfied — `.owlbear/research/1865-resolve-decision-extraction.md` exists and is linked in task body.

### Item 4: Deletion Detection
N/A — moved helpers were internal (prefixed `_`), never documented in any README. No orphaned references.

### Scratch Cleanup
No `1865-*` scratch files found.

[[2026-05-25T06:50:10+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 422 passed, 30 failed (all pre-existing in unrelated domains: error_envelope, kanban_routes, cache_sse, cache_populate; last modified well before task commits)
- Consolidation backstop (tests/test_cockpit_decisions_api.py): 89 passed, 0 failed
- Task-scoped tests (tests/test_decisions_1868.py): 28 passed, 0 failed
- Lint violations: 29 total, all in serve/knowledge/ (unrelated domain)
- regression verdict: PASS (no new failures introduced by this task or its children)

### Intent Verification
- scope alignment: PASS (umbrella task decomposes into scope:kanban #1868 and scope:cockpit-backend #1869, both archived)
- purpose match: PASS (extract resolve_decision into kanban module and delegate from Cockpit, both delivered)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Final AC is clear and verifiable (2 lines gating on child completion + consolidation proof). Required one reviewer-driven refinement cycle to replace metadata-only closure with feature-closure criteria. Architecture decomposition was thorough with failure mode maps and FileNotFoundError contract propagation. Score reflects the needed iteration.

### Commit Integrity
- upstream commit presence: PASS (c270ac0e builder #1868, 620a33bc builder #1869, plus test-writer commits 35d00c0c, cd3552fc, 1a87f5d3)
- builder commit scope: PASS (parent is umbrella with no source commits; children each scoped to single files)
- kanban commit packaging: pending (this commit)

### Deduction Breakdown
None applied. All criteria clean.

### Confidence: 1.00
### Action: archive
