---
id: 1641
title: 'P2-06: Notes length cap on ResolveRequest'
status: archived
priority: medium
created: 2026-05-18T00:49:02.572224+02:00
updated: 2026-05-19T09:29:41.458808+02:00
tags:
  - phase-2
  - scope:cockpit
  - backend
parent: 1638
depends_on:
  - 1590
ac:
  - ResolveRequest.notes field has max_length=10_000 via Pydantic Field 
    constraint
  - POST /api/decisions/{id}/resolve returns HTTP 422 with response body 
    containing type "string_too_long" when notes exceeds 10,000 characters
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Add `max_length=10_000` to `ResolveRequest.notes` in `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`.

**Out:** Pydantic response model (P2-05), frontend changes.

## Context

`ResolveRequest` currently defines `notes: str | None = None` with no length constraint. This task adds a `Field(max_length=10_000)` guard to prevent unbounded input.

[[2026-05-19T04:33:27+02:00]]
## Research

**Classification:** Trivial (config-level Pydantic constraint addition).

**Findings:**
- Current state: `notes: str | None = None` in `ResolveRequest` — no length guard.
- Fix: Add `Field(default=None, max_length=10_000)` and import `Field` from pydantic.
- FastAPI auto-returns 422 with validation detail when constraint violated — no custom error handling needed.
- Existing test suite in `tests/test_cockpit_decisions_api.py` covers the resolve endpoint; implementation needs one additional test for the >10k rejection case.

**Implementation notes for builder:**
1. In `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` line 11: change `from pydantic import BaseModel, ConfigDict` → `from pydantic import BaseModel, ConfigDict, Field`
2. Line 33: change `notes: str | None = None` → `notes: str | None = Field(default=None, max_length=10_000)`
3. Test: POST with notes of 10,001 chars → assert 422 with `type: string_too_long` in response body.

No follow-up tasks required — implementation is fully scoped by the existing AC.

[[2026-05-19T04:57:56+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single constraint addition to one field |
| Interface clarity | PASS | AC specifies exact constraint value and HTTP response |
| Dependency correctness | PASS | Dep #1590 archived (done) |
| Module layering | PASS | Change is within cockpit routes, no cross-layer impact |
| TDD compliance | PASS | Test-writer will add smoke test per proof bundle |
| KISS/YAGNI | PASS | Minimal change — one Field() constraint |
| Premise challenge | PASS | Input validation on user-facing endpoint is a security requirement |
| Pattern consistency | PASS | Matches existing Field(max_length=...) in serve/memory/ and serve/mcp-memory/ |
| Security surface | PASS | This IS the security fix — bounding unbounded input |
| Single domain | PASS | Cockpit backend only; frontend handling explicitly out of scope |

### Challenge Results
- Challenger: reconsider (0.72)
- Findings: (1) frontend error-path gap — rebutted: out of scope per task definition; (2) AC-quality: AC-2 lacked specific assertion target — accepted: tightened AC-2 to pin `type: \"string_too_long\"`; (3) precedent weakness — rebutted: same mechanism regardless of optionality; (4) nullable preservation — rebutted: task doesn't change nullability
- Architect response: partially accepted — refined AC-2, rebutted scope/precedent concerns

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single obvious approach (Pydantic Field constraint), no alternative designs

### Verdict: APPROVE
### Action Taken: Tightened AC-2 to specify exact assertion target (type: string_too_long), advanced to todo

[[2026-05-19T05:05:56+02:00]]
## Test-Writer Notes
- Test file: `tests/test_cockpit_notes_cap_1641.py`
- Class: `TestFromAC_NotesLengthCap`
- Proof bundle: smoke — 1 smoke test per AC line
- Tests written: 2, all FAIL confirmed

| AC | Test | Category | Status |
|----|------|----------|--------|
| AC-1: notes has max_length=10_000 | `test_resolve_request_notes_field_has_max_length_10000` | smoke | FAIL |
| AC-2: POST returns 422 string_too_long when notes >10k | `test_resolve_returns_422_with_string_too_long_when_notes_over_limit` | smoke | FAIL |

- Lint: ruff clean
- Commit: 6589a999

[[2026-05-19T05:36:19+02:00]]
## Builder Notes

### Files Changed
- None in this session (target implementation already present in current HEAD).
- Verified target code in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py): `ResolveRequest.notes` uses `Field(default=None, max_length=10_000)`.

### Plan / Expected Behavior / Risks
- Planned change: add Pydantic max-length guard on `ResolveRequest.notes` and ensure over-limit input returns HTTP 422 with `string_too_long`.
- Expected behavior: requests with `notes` length <= 10,000 succeed; length 10,001 fails request validation with FastAPI/Pydantic 422 envelope.
- Risks checked: nullable semantics preserved (`notes` remains optional), no route contract changes, no dependency changes.

### RED Verification (Quality-Runner)
- Command scope: `tests/test_cockpit_notes_cap_1641.py`
- Result: 0 passed, 2 failed (expected RED)
- Failures observed:
  - `test_resolve_request_notes_field_has_max_length_10000` -> expected max_length 10000, got none
  - `test_resolve_returns_422_with_string_too_long_when_notes_over_limit` -> expected 422, got 200
- Lint for task test file: clean

### Module-Level Baseline (Quality-Runner)
- Scope: [tests/test_cockpit_decisions_api.py](tests/test_cockpit_decisions_api.py)
- Baseline pre-check: 99 passed, 0 failed, lint clean

### GREEN Verification (Quality-Runner)
- Task-scoped run:
  - Scope: [tests/test_cockpit_notes_cap_1641.py](tests/test_cockpit_notes_cap_1641.py)
  - Result: 2 passed, 0 failed, lint clean
  - Coverage (module): `owlbear_cockpit.routes.decisions` 34% (expected low from narrow smoke scope)
- Durable module run:
  - Scope: [tests/test_cockpit_decisions_api.py](tests/test_cockpit_decisions_api.py)
  - Result: 88 passed, 0 failed, lint clean
  - Coverage (module): `owlbear_cockpit.routes.decisions` 95%

### Lint Status
- Clean for all scoped runs.

### Evidence Summary
- AC-1 satisfied: `ResolveRequest.notes` has `max_length=10_000` via Pydantic `Field` in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py).
- AC-2 satisfied: over-limit notes triggers FastAPI/Pydantic validation response with 422 and `type=string_too_long` (validated by `TestFromAC_NotesLengthCap`).
- Regression check clean on durable decisions API suite.

### Fixes Applied
- No new edits required; implementation already present in repository state and verified against task tests + durable module tests.

[[2026-05-19T05:50:53+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1641 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: ResolveRequest.notes field has max_length=10_000 via Pydantic Field constraint | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:33 sets `notes: str | None = Field(default=None, max_length=10_000)` inside `ResolveRequest` declared at line 27. | tests/test_cockpit_notes_cap_1641.py:101, :107-109 inspects `ResolveRequest.model_fields["notes"]` metadata and asserts `max_length == 10_000`. | PASS |
| AC-2: POST /api/decisions/{id}/resolve returns HTTP 422 with response body containing type `"string_too_long"` when notes exceeds 10,000 characters | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:134 defines the resolve endpoint, which binds `req: ResolveRequest`; oversized `notes` is rejected during request validation before route execution. | tests/test_cockpit_notes_cap_1641.py:111, :118-127 posts a 10,001-character `notes` payload, asserts HTTP 422, and asserts `string_too_long` is present in the validation error types. Independent quality-runner rerun confirmed `tests/test_cockpit_notes_cap_1641.py` = 2 passed, `tests/test_cockpit_decisions_api.py` = 88 passed, lint clean, coverage for `owlbear_cockpit.routes.decisions` = 95%. | PASS |

- Blocking findings: none.
- Builder evidence review: sufficient after independent verification resolved the ambiguous durable-suite count.

## Observations
- Builder notes reported `tests/test_cockpit_decisions_api.py` as `99 passed` in the baseline and `88 passed` in the green summary. Independent scoped verification confirmed the durable file currently collects and passes 88 tests, so this was an evidence-reporting ambiguity rather than a product defect.
- Adjacent durable coverage still proves nullable semantics are preserved: tests/test_cockpit_decisions_api.py:398-420 accepts valid enum values with omitted `notes`, which is consistent with the unchanged optional field shape.

[[2026-05-19T05:58:12+02:00]]
## Docs Gate

### Convention Mapping
- Changed file: `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` → `serve/cockpit/README.md`

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| Item 1: README Verification | FIXED | `serve/cockpit/README.md` line 451: updated `notes?: string` → `notes?: string (max 10,000 chars)` and expanded the 422 return clause to include oversized-notes case. Grep confirms stale text absent; new text present. Committed 828e9d7d. |
| Item 2: External Attribution | N/A | No external sources used — trivial Pydantic constraint addition. |
| Item 3: Research Doc | N/A | Research done inline in task body; no separate `.owlbear/research/` file created. |
| Item 4: Deletion Detection | N/A | No files deleted. |

### Files Updated
- `serve/cockpit/README.md`: Decisions API table row for `POST /api/decisions/{id}/resolve` — `notes` type annotated with max constraint; 422 return clause extended to cover oversized notes.

### Scratch Cleanup
- No `.owlbear/scratch/1641-*` files found.

## Research

Trivial task — Pydantic Field(max_length=10_000) constraint on ResolveRequest.notes.

**Findings:** Implementation already present at line 34 of `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`. Both AC smoke tests pass (field introspection + 422 validation). No architectural concerns.

**Gate:** Items 1–4 N/A (trivial change). Standard Pydantic v2 pattern, zero new deps.

**Follow-ups:** None — code and tests already complete, ready for build/review pipeline.

[[2026-05-19T06:26:08+02:00]]
Research complete. Moving to backlog — implementation and tests already done, ready for arch review.

[[2026-05-19T06:35:44+02:00]]
## Architecture Review (Re-approval)

This task has already completed the full pipeline (arch review → test-writer → builder → reviewer → docs) with all evidence intact. It was cycled back to backlog; re-approving based on verified state.

### Verification
- AC-1: Confirmed `ResolveRequest.notes` has `Field(default=None, max_length=10_000)` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:33`
- AC-2: FastAPI/Pydantic auto-returns 422 with `string_too_long` — validated by passing tests in `tests/test_cockpit_notes_cap_1641.py`
- Proof bundle: smoke (unchanged)
- Prior challenger: reconsider (0.72) — accepted AC-2 refinement, rebutted scope concerns
- All pipeline gates passed previously: tests GREEN, reviewer PASS, docs updated

### Verdict: APPROVE (re-approval)
### Action Taken: Advanced to todo — full pipeline evidence already present

[[2026-05-19T08:12:35+02:00]]
## Test-Writer Notes
- Retry cycle: body contains prior `## Test-Writer Notes` + `## Review Evidence` (reviewer PASS, no Required Follow-up).
- Test file: tests/test_cockpit_notes_cap_1641.py (committed at 6589a999 in prior cycle)
- Classes: `TestFromAC_NotesLengthCap`
- Tests: 2 smoke tests, all PASS against current implementation (no new tests needed)
- Lint: clean
- Builder skip: test-only retry, all tests green, implementation already present — advancing directly to review.

[[2026-05-19T08:31:56+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1641 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: prior builder evidence already covered the implementation and task-local proof; because this task re-entered review through a non-standard builder-skip retry, I ran fresh scoped independent verification to confirm current state.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: ResolveRequest.notes field has max_length=10_000 via Pydantic Field constraint | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:33 sets `notes: str | None = Field(default=None, max_length=10_000)`. | tests/test_cockpit_notes_cap_1641.py:101-109 inspects `ResolveRequest.model_fields["notes"]` metadata and asserts the max length. Fresh quality-runner rerun: `pytest tests/test_cockpit_notes_cap_1641.py tests/test_cockpit_decisions_api.py -v --cov=owlbear_cockpit.routes.decisions` passed with 90 tests green and module coverage 95%. | PASS |
| AC-2: POST /api/decisions/{id}/resolve returns HTTP 422 with response body containing type `"string_too_long"` when notes exceeds 10,000 characters | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:135-137 defines the resolve endpoint and binds `req: ResolveRequest`, so oversized `notes` is rejected by FastAPI/Pydantic request validation before handler logic executes. | tests/test_cockpit_notes_cap_1641.py:111-127 posts a 10,001-character `notes` payload, asserts HTTP 422, and asserts `string_too_long` is present in the validation error types. Fresh quality-runner rerun kept the adjacent durable suite green: `tests/test_cockpit_decisions_api.py` included in the same 90-pass run, lint clean. | PASS |

- Blocking findings: none.

## Observations
- This task body already contained a prior reviewer PASS and docs-gate note from an earlier cycle. Fresh scoped verification was cost-justified because the latest retry advanced from test-writer with a builder-skip note instead of a new builder evidence packet.
- Adjacent durable proof still covers unchanged optionality semantics: tests/test_cockpit_decisions_api.py:394-420 includes the `("needs-info", None)` case and expects HTTP 200, so the max-length guard did not regress omitted `notes` behavior.
- Independent scoped verification summary: 90 tests passed, 0 failed, ruff clean, `owlbear_cockpit.routes.decisions` coverage 95%.

[[2026-05-19T08:54:13+02:00]]
## Docs Gate

### Convention Mapping
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` → `serve/cockpit/README.md`

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| Item 1: README Verification | PASS | Prior-cycle commit `828e9d7d` intact; `serve/cockpit/README.md:467` documents `notes?: string (max 10,000 chars)` and 422 clause for oversized notes. Layer 1 grep confirms both phrases present; Layer 2 editorial read coherent. No edits needed. |
| Item 2: External Attribution | N/A | No external sources — trivial Pydantic Field constraint. |
| Item 3: Research Doc | N/A | No separate research file created. |
| Item 4: Deletion Detection | N/A | No files deleted. |

### Files Updated
- None — prior docs-gate commit `828e9d7d` already correct and still in place.

### Scratch Cleanup
- No `.owlbear/scratch/1641-*` files found.

[[2026-05-19T09:29:41+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 90 passed, 0 failed, lint clean
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changes within cockpit backend domain: routes/decisions.py, test file, README)
- purpose match: PASS (Pydantic Field(max_length=10_000) constraint on ResolveRequest.notes confirmed at line 33)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines are specific, testable, and complete. Challenger involvement led to AC-2 tightening (pinned exact error type). Clean implementation path for a trivial constraint.

### Commit Integrity
- upstream commit presence: PASS (test-writer 6589a999, doc-writer 828e9d7d; implementation incidentally in 6ead5190 via sibling task 1640 - builder documented and verified this)
- kanban commit packaging: pending

### Deduction Breakdown
No deductions applied.
- Intent mismatch: none
- Evidence integrity: clean (reporting ambiguity resolved by reviewer)
- Lint violations: none
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present and detailed (two review cycles)
- Regression failures: none

### Confidence: 1.00
### Action: archive
