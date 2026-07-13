---
id: 1390
title: 'P2-15: Guard Cockpit steering viewport product boundary'
status: archived
priority: medium
created: 2026-05-06T01:04:54.084895+00:00
updated: 2026-05-07T08:16:07.693135+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit
- type:docs
- type:test
- product-boundary
- guardrail
parent: 1363
depends_on:
- 1371
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Preserve the approved product boundary that Cockpit is a steering viewport, not a duplicate planner or agent lifecycle surface.

## Product Decision
Cockpit remains responsible for viewing, editing, moving or archiving, user blocks, health/admin, activity, and decision resolution. Task creation and agent lifecycle actions remain owned by agents, planner flows, and MCP unless a future explicit product brief changes this boundary.

## Acceptance Criteria
- Documentation and/or visible handoff copy make the Cockpit steering-viewport boundary explicit enough that future work does not accidentally add duplicate planner or MCP lifecycle controls.
- API allowlist documentation and tests or assertions continue to exclude create_task, claim/start_work, and end_work from Cockpit routes.
- UX handoff points direct users toward planner, agent, or MCP flows for task creation, claim/start, and release/end-work needs rather than adding lifecycle buttons.
- Existing valid Cockpit steering actions remain available: viewing, editing, moving or archiving, user blocks, health/admin, activity, and decision resolution.
- Verification confirms no new Cockpit route or UI affordance exposes create_task, claim/start_work, or end_work without a future explicit product brief.

## Scope
- In scope: Cockpit product-boundary docs, route allowlist guardrails, tests or assertions, and any minimal handoff copy needed to prevent drift.
- Out of scope: implementing create_task UI, claim/start_work UI, end_work UI, removing existing valid steering actions, and cache/SSE invalidation from #1346.

## Notes
This is intentionally a single guardrail task rather than a TDD implementation pair because it protects product authority through documentation and allowlist assertions, not a new functional workflow.

[[2026-05-06]]


## Architecture Review

### AC Assessment
| AC Line (original) | Assessment | Action |
|---|---|---|
| AC1: Documentation makes boundary explicit | REDUNDANT — README.md "Excluded methods — why" section already exists | Merge into AC about verifying/maintaining the existing doc |
| AC2: Tests exclude create_task, start_work, end_work | GOOD but needs specificity — what test form? | Tighten to route-level HTTP assertion |
| AC3: UX handoff points | VAGUE — no create-task UI exists to put handoff copy on; "handoff points" undefined | Reframe as developer-facing guardrail comment |
| AC4: Existing steering actions remain available | REDUNDANT — existing test suites already cover all route contracts | Drop; regression covered by existing suites |
| AC5: No new route exposes excluded methods | OVERLAPS AC2 | Merge into AC2 |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: guard the product boundary |
| Interface clarity | FAIL (pre-refine) | AC3 "UX handoff points" undefined; AC4/AC5 overlap AC2; after refinement: PASS |
| Dependency correctness | PASS | #1371 archived (done) |
| Module layering | N/A | No production code changes |
| TDD compliance | PASS | Tagged type:test — test-writer passes through, builder writes boundary tests |
| KISS/YAGNI | PASS after refinement | Minimal guardrail scope once redundant AC removed |
| Premise challenge | PASS | AST boundary exists but route-level HTTP assertion is a valid new guardrail layer |
| Pattern consistency | PASS | Extends existing test_cockpit_boundary.py pattern |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit only |

### Refined Acceptance Criteria
See updated AC below (rewritten from 5 vague lines to 3 verifiable lines).

### Challenge Results
- Challenger: SKIPPED — td:1 max but straightforward guardrail extension; no design divergence; single obvious approach (extend test_cockpit_boundary.py with HTTP-level route assertions)

### Test Depth
- Max depth: td:1

### Verdict: APPROVE (after AC refinement applied below)

[[2026-05-06]]


## Refined Acceptance Criteria (replaces original AC)
- `tests/test_cockpit_boundary.py` contains a new test class that instantiates the FastAPI `TestClient` and asserts HTTP 404 or 405 for `POST /api/tasks/create`, `POST /api/tasks/{id}/claim`, `POST /api/tasks/{id}/start`, and `POST /api/tasks/{id}/end-work` — proving no lifecycle routes exist at the HTTP surface (td:1)
- `serve/cockpit/README.md` "Excluded methods — why" section remains present and lists `create_task()`, `claim_task()` / `start_work()` / `end_work()` with exclusion reasons; section includes a note that adding these routes requires an explicit product brief (td:0)
- The existing AST-level import boundary scan in `test_cockpit_boundary.py` (checking `_FORBIDDEN_NAMES`) continues to pass (td:0 — already covered by existing test)

## Builder Guidance
- Extend `tests/test_cockpit_boundary.py` with a new test class (e.g., `TestFromAC_RouteExclusionGuardrail`) that uses the existing test fixtures and `TestClient` pattern from the file.
- The README update is a one-line addition to the existing "Excluded methods — why" section footer.
- Do NOT add any new routes, production code, or UI components.

[[2026-05-06]]
Architecture review complete. Refined 5 vague/overlapping AC lines into 3 precise verifiable criteria: (1) route-level HTTP 404/405 assertions for excluded lifecycle endpoints (td:1), (2) README exclusion section maintenance (td:0), (3) existing AST boundary scan continues passing (td:0). Codebase already has import-level guardrail in test_cockpit_boundary.py and docs in serve/cockpit/README.md — this task adds the missing HTTP-surface layer. Approved to todo.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged type:test, type:docs) — no tests applicable.
- Architect confirmed in task body: "test-writer passes through, builder writes boundary tests."
- The builder's deliverable is (1) a new `TestFromAC_RouteExclusionGuardrail` class in `tests/test_cockpit_boundary.py` with HTTP 404/405 assertions for excluded lifecycle routes and (2) a one-line README addition — both are the task's output artifacts, not inputs that can be tested in RED phase.
- AC2 (README section) and AC3 (existing AST scan) are both td:0 — also no test-writer action required.
- Passing through to builder.
[[2026-05-07]]
## Builder Notes
- Implementation: no file edits required in this build pass; required guardrails already present in `tests/test_cockpit_boundary.py` and `serve/cockpit/README.md`.
- Tests: 24 passed in scoped run (`tests/test_cockpit_boundary.py`), 0 failed.
- Coverage: 36% overall for `owlbear_cockpit` package in scoped run (informational; no production module changes in this pass).
- ruff: clean (no violations in `tests/test_cockpit_boundary.py`).
- Evidence summary: `TestFromAC_RouteExclusionGuardrail` asserts POST 404/405 for `/api/tasks/create`, `/api/tasks/{id}/claim`, `/api/tasks/{id}/start`, `/api/tasks/{id}/end-work`; README excluded-methods section includes explicit product-brief requirement for exposing lifecycle routes.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 24 passed, 0 failed, 0 skipped on `tests/test_cockpit_boundary.py`
- Route guardrail proof is present in `TestFromAC_RouteExclusionGuardrail` at `tests/test_cockpit_boundary.py:258`; the parametrized POST targets are listed at `tests/test_cockpit_boundary.py:269-275`, and the discriminating assertion is `response.status_code in (404, 405)` at `tests/test_cockpit_boundary.py:278`
- No test failures or flaky behavior were reported by quality-runner

### Lint Results
- quality-runner ruff pass is clean for `serve/cockpit/src/` and `tests/test_cockpit_boundary.py`

### Coverage
- quality-runner reports low overall `owlbear_cockpit` module coverage in untouched production files (`mutation.py` 36%, `view.py` 25%, `events.py` 24%)
- Non-blocking for this task: the reviewable scope is docs/test guardrails, and the live task-owned assertions fully exercise the refined AC surface

### Scope / Ownership Checks
- No prior `## Review Evidence` sections found in the task body; this is the first review cycle
- One `## Builder Notes` section found; builder loop detection = CLEAN
- Task-specific builder commit presence is corroborated by `.git/logs/refs/heads/dev:1985` (`commit: test: enforce cockpit lifecycle boundary routes (#1390, builder)`), so this is not a stale verification-only child task

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| `tests/test_cockpit_boundary.py` contains a new TestClient-based guardrail asserting POST 404/405 for `/api/tasks/create`, `/api/tasks/{id}/claim`, `/api/tasks/{id}/start`, `/api/tasks/{id}/end-work` | `tests/test_cockpit_boundary.py:258`, `tests/test_cockpit_boundary.py:269-278`; quality-runner: 24 passed, 0 failed | PASS |
| `serve/cockpit/README.md` excluded-methods section remains present and requires an explicit product brief before exposing lifecycle routes | `serve/cockpit/README.md:39-47` lists `create_task()`, `claim_task()` / `start_work()` / `end_work()` as excluded and adds the explicit-product-brief note | PASS |
| Existing AST-level boundary scan for forbidden cockpit imports continues to pass | `_FORBIDDEN_NAMES` is defined at `tests/test_cockpit_boundary.py:23`; guard tests remain present at `tests/test_cockpit_boundary.py:208`, `tests/test_cockpit_boundary.py:219`, `tests/test_cockpit_boundary.py:230`, `tests/test_cockpit_boundary.py:239`; quality-runner: 24 passed, 0 failed | PASS |

### Test Quality Assessment
- Assertion specificity: STRONG. The HTTP guardrail fails if any excluded POST route is added and returns a normal route status (for example 200, 201, 409, 422, 500)
- Negative-path coverage: ADEQUATE for td:1. The task contract is itself a negative surface assertion
- Test integrity: no evidence of weakened assertions in the current snapshot
- Security/data-safety review: no new dependency, secret, injection, or persistence surface added by this task

### Deductions
- -0.03 confidence: current tool surface did not provide a direct commit diff for diff-level `TestFromAC_*` immutability verification; assessment relies on the live snapshot plus task-specific git-log commit evidence

### Verdict
PASS -> docs | confidence 0.95

### Action
- Advance to docs
- No follow-up required

### Post-task Reflection
- Current repo state and task-owned artifacts aligned cleanly with the refined AC
- Git-log reconstruction was enough to clear the stale-no-op concern without a direct diff
- Low module-level coverage was residual package debt, not a task-owned blocker, because this task changed only boundary proofs and docs
[[2026-05-07]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A (already compliant) | `serve/cockpit/README.md` "Excluded methods — why" section present at lines 39-47; lists `create_task()`, `claim_task()` / `start_work()` / `end_work()` with exclusion reasons; product-brief note already included — no changes needed |
| 2 | Module docstrings | Yes | N/A (already accurate) | `tests/test_cockpit_boundary.py`: `TestFromAC_RouteExclusionGuardrail` class docstring present; `client` fixture and `test_excluded_lifecycle_post_routes_not_available` method docstrings present and accurate |
| 3 | External attribution | No | N/A | No external patterns or articles referenced by builder |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | `cockpit.excalidraw` describes `serve/cockpit/src/**` and `serve/cockpit/web/src/**`; changed files (`tests/test_cockpit_boundary.py`, `serve/cockpit/README.md`) do not match those globs |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `tests/test_cockpit_boundary.py` | IN (docstrings) | Verified accurate — no changes needed |
| `serve/cockpit/README.md` | IN (Package README) | Verified compliant — no changes needed |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found for task #1390
[[2026-05-07]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_RouteExclusionGuardrail asserts POST 404/405 for excluded lifecycle routes | tests/test_cockpit_boundary.py:258-283; parametrized paths at L269-275; assertion at L278; quality-runner scoped: 24 passed | PASS |
| README excluded-methods section with product-brief requirement | serve/cockpit/README.md:39-47; lists create_task, claim_task/start_work/end_work; explicit-brief note present | PASS |
| Existing AST boundary scan continues to pass | _FORBIDDEN_NAMES at L23; guard tests at L208,219,230,239; quality-runner: 24 passed | PASS |

### Test Results
- pytest full suite: 4767 passed, 219 failed (all pre-existing background debt in unrelated modules: engine accessor, state machine, memory model), 0 failures in task scope
- vitest: 992 passed, 0 failed
- ruff: 12 violations all in unrelated packages; 0 in task scope

### Commit Verification
- Builder commit confirmed: 9ca60cd5 "test: enforce cockpit lifecycle boundary routes (#1390, builder)"

### Architect Quality: 4/5
Original 5 AC lines were vague and overlapping (would score 2-3); architect self-refined to 3 precise verifiable criteria. Final product was specific and testable. Minor gap: initial quality required significant rewrite before builder could proceed.

### Deduction Breakdown
- AC lines without evidence: 0 (no deduction)
- Lint in task scope: 0 (no deduction)
- AC quality: 4/5 (no deduction; threshold is 3 or below)
- Reviewer evidence: present and detailed (no deduction)
- Full-suite failures in task scope: 0 (no deduction)

### Confidence: .98
### Action: archive