---
id: 1865
title: 'Kanban: expose resolve_decision() and delegate from Cockpit'
status: backlog
priority: important
created: 2026-05-25T00:06:59.303292+02:00
updated: 2026-05-25T01:19:21.527971+02:00
tags:
  - scope:kanban
  - scope:cockpit-backend
  - boundary-audit
  - quality
parent:
depends_on: []
ac:
  - 'Children #1868 and #1869 exist with parent=1865, single-domain scope tags, and
    dependency chain #1869 depends_on #1868'
  - '#1868 is scoped to owlbear_kanban.decisions only (scope:kanban tag)'
  - '#1869 is scoped to owlbear_cockpit.routes.decisions only (scope:cockpit-backend
    tag)'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
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
