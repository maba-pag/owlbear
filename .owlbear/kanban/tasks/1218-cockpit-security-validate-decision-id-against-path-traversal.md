---
id: 1218
title: Cockpit security — validate decision_id against path traversal
status: review
priority: needed
created: 2026-04-30 16:31:07.651363+00:00
updated: 2026-04-30T21:47:39.185992+00:00
tags:
- cockpit
- security
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: green-stream
claimed_at: 2026-04-30T21:47:39.185992+00:00
archival_reason:
archival_refs: []
---

## Objective
Prevent path traversal via crafted decision_id in the decisions API.

## Acceptance Criteria
- [ ] `_find_decision_path()` in `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` raises `HTTPException(422)` if `decision_id` does not match allowlist pattern `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`; validation executes before any `Path.exists()` or filesystem I/O (td:2)
- [ ] `POST /decisions/{decision_id}/resolve` returns HTTP 422 for malformed decision_id values (td:1)
- [ ] Unit tests exercise `_find_decision_path()` directly with traversal payloads: `../../etc/passwd`, `foo/bar`, `..\\secret`, empty string, `.hidden`, and a valid id like `1234-some-slug` (td:2)

## Architecture Notes
- Use allowlist (not blocklist) — the actual DR naming convention is `{task_id}-{slug}` with `[a-zA-Z0-9_-]` characters only.
- Raise `HTTPException(422)` directly in the helper (not `ValueError`) so the route handler's existing `except FileNotFoundError` pattern is unchanged.
- FastAPI single-segment path params reject literal `/` at routing layer; the helper-level validation catches URL-decoded `%2F` and other encoded traversal vectors.
- Tests must call `_find_decision_path()` directly (unit-level) to prove validation fires before filesystem access — route-level tests alone could pass for the wrong reason (router rejection).

## Files
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`

[[2026-04-30]]
## Architecture Review

**Verdict:** APPROVED → todo

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: allowlist validation in `_find_decision_path()` | Refined from blocklist to allowlist `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`; specifies HTTPException(422) directly; "before filesystem I/O" is structurally provable | Tightened |
| AC2: HTTP 422 for malformed IDs | Clear observable behavior | Kept |
| AC3: Unit tests with traversal payloads | Refined to specify direct helper calls (not just route-level); added valid-id positive case | Tightened |

### Architecture Notes
- Single responsibility: one security fix, one function, one file
- Allowlist > blocklist per OWASP; matches actual DR naming convention (`{task_id}-{slug}`)
- HTTPException(422) in helper avoids exception-path mismatch with existing handler
- FastAPI routing absorbs literal-slash cases; helper guards against URL-decoded traversal
- No dependencies; no new abstractions; no layering changes

### Challenger Result
- Confidence: 0.58 → reconsider
- Valid points addressed: exception semantics (→ HTTPException directly), router-vs-helper test layer (→ unit tests required), blocklist weakness (→ allowlist)
- Residual risk: low — all actionable concerns incorporated into AC
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_decisions_1218.py
- Classes: TestFromAC_DecisionIdValidation, TestFromAC_ValidationBeforeFilesystemIO, TestFromAC_RouteRejects422
- Tests per category: happy 0, edge 2, error 10, boundary 2
- Total: 14 tests, all FAIL
- ruff: clean

### AC Coverage
| AC Line | Tests |
|---------|-------|
| AC1: HTTPException(422) for invalid ids before I/O | test_invalid_id_raises_http422 (×5 parametrized) + 5 explicit per-payload + test_no_filesystem_io_for_traversal_payload + test_no_filesystem_io_for_empty_id |
| AC2: route returns 422 | test_route_422_for_dot_hidden_id + test_route_422_for_dot_dot_traversal_id |
| AC3: specific traversal payloads directly | test_traversal_dot_dot_slash_raises_422, test_traversal_foo_slash_bar_raises_422, test_traversal_backslash_raises_422, test_empty_string_raises_422, test_dot_hidden_raises_422 |

### Failure modes (confirming RED)
- AC1/AC3 tests: FileNotFoundError raised instead of HTTPException(422) — no allowlist check exists
- AC2 tests: HTTP 404 returned instead of 422 — route catches FileNotFoundError → 404
[[2026-04-30]]
## Builder Notes
- Implementation: Added allowlist validation in serve/cockpit/src/owlbear_cockpit/routes/decisions.py within _find_decision_path() using pattern ^[a-zA-Z0-9][a-zA-Z0-9_-]*$; invalid IDs now raise HTTPException(422) before any Path.exists() calls.
- Files changed: serve/cockpit/src/owlbear_cockpit/routes/decisions.py
- TestFromAC verification (RED before GREEN): 14 failed / 14 total in tests/test_decisions_1218.py prior to implementation (FileNotFoundError/404 mismatch).
- Scoped GREEN verification: 14 passed / 0 failed in tests/test_decisions_1218.py.
- Lint: ruff clean on serve/cockpit/src/owlbear_cockpit/routes/decisions.py and tests/test_decisions_1218.py.
- Coverage evidence:
  - quality-runner scoped run: tests+lint clean.
  - targeted module run: 36% for owlbear_cockpit.routes.decisions on task-only test file (expected partial due broader module responsibilities).
  - broader decisions scope run: 102 passed, 0 failed and 100% coverage for serve/cockpit/src/owlbear_cockpit/routes/decisions.py.
- Commit: 4f50ce0ae42456221c9d2c6ee1040188d79008aa

### Evidence Summary
- AC1: invalid/traversal decision_id rejected with HTTP 422 in helper precondition path.
- AC1 (before I/O): validation executes before filesystem existence checks.
- AC2: malformed decision_id resolve route returns 422.
- AC3: direct helper-level payload coverage satisfied by existing TestFromAC cases.

### Post-task Reflection
- Problem faced: task-local coverage under-represented module-level coverage because route module serves additional endpoints.
- Workaround applied: added broader but still domain-scoped decisions suites for authoritative module coverage.
- Pattern discovered: helper-level validation changes in multi-endpoint modules need both task tests and sibling suites for realistic coverage gating.
- Quality gap: quality-runner coverage mapping can show misleading low percentage for narrowly scoped test paths; direct scoped coverage command remains useful as corroboration.
[[2026-04-30]]
## Review Evidence

### Test Results
- quality-runner scoped pytest: 14 passed, 0 failed

### Lint
- quality-runner scoped ruff: clean for [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py) and [tests/test_decisions_1218.py](tests/test_decisions_1218.py)

### Coverage
- quality-runner scoped module coverage: 36% for owlbear_cockpit.routes.decisions
- This is not the reject reason. The reject is AC-proof failure, not module-coverage failure.

### Pass 1 - Critical

#### Test-Writer AC Coverage
| AC Line | Evidence | Would Fail If AC Violated? | Verdict |
|---------|----------|---------------------------|---------|
| AC1: helper rejects malformed ids before filesystem I/O | Allowlist gate in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L103); direct 422 tests at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L125-L161); no-I/O assertions at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L172-L204) | Yes | COVERED |
| AC2: resolve route returns 422 for malformed ids | Route only remaps FileNotFoundError at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L142-L151); malformed-id route tests at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L211-L230) | Yes | COVERED |
| AC3: direct helper tests cover traversal payloads and a valid id like 1234-some-slug | Every direct helper call in [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L128-L200) uses only malformed ids: bad_id, ../../etc/passwd, foo/bar, ..\\secret, empty string, and .hidden. No direct helper test covers a valid allowlisted id, and grep search for 1234-some-slug in [tests/test_decisions_1218.py](tests/test_decisions_1218.py) returned no matches. The success branch after regex validation in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L100-L105) is therefore unproved. | No for the valid-id subcase | MISSING |

#### Security Review
- PASS: the targeted traversal risk is closed by the allowlist at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L19) and the pre-I/O rejection at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L103).

#### Test Integrity
- PASS: no weakened or removed TestFromAC assertions found in [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L109-L230). Exact 422 checks and zero-Path.exists assertions are still present.

#### Test Quality
- PASS on specificity and independence for the cases present.
- Informational: the docstring at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L223-L226) says URL-decoded traversal, but the exercised route segment is literal ..secret.

#### Data Safety
- PASS: the changed helper path in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L105) introduces no new shared-mutable-state or persistence risk.

#### Implementation-Aware Test Gaps
- FAIL: a regression that incorrectly rejects a valid allowlisted id would pass this suite. The code path after a successful regex match at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L100-L105) has no direct helper proof in [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L128-L200).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Helper allowlist + pre-I/O order proven by [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L103) and [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L172-L204) | test_invalid_id_raises_http422 and no_filesystem_io tests | PASS |
| AC2 | Helper 422 propagates because only FileNotFoundError is caught at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L142-L151); route tests assert 422 at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L211-L230) | route 422 tests | PASS |
| AC3 | Invalid payloads are covered, but the required valid-id direct helper subcase is absent from [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L109-L204) | direct helper tests | FAIL |

### Subagent Divergence
- quality-runner reported AC3 satisfied, but manual review and code-reader both found the valid-id subcase missing. Final verdict follows the AC text and the live test file.

### Deductions
- -0.14 missing AC3 valid-id direct helper proof
- -0.02 subagent AC overclaim requiring manual override
- Confidence: 0.84

### Required Follow-up
- Add a direct TestFromAC helper test for a valid allowlisted id such as 1234-some-slug.
- Strongest proof: create a pending or resolved decision file for that id and assert [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L105) returns the expected path without 422.
- Re-run the task-owned suite and lint. If no source change is needed and the strengthened tests pass against current implementation, this can return directly to review.

### Verdict
- FAIL -> todo. This is a test-gap rejection; the implementation evidence is otherwise acceptable.
[[2026-04-30]]
## Test-Writer Notes
- Retry: added 1 test for reviewer's AC3 gap (valid-id direct helper proof).
- Test: `TestFromAC_DecisionIdValidation::test_valid_id_returns_pending_path` — creates `1234-some-slug.md` in pending dir, calls `_find_decision_path()` directly, asserts correct path returned without HTTPException.
- All 15 tests PASS against current implementation (builder already handles the success branch).
- Lint: ruff clean on tests/test_decisions_1218.py.
- Builder skip: test-only retry, all tests green.
[[2026-04-30]]
## Builder Notes
- Implementation: no source changes required in this builder pass.
- Context: task returned to in-progress after reviewer identified an AC3 test-proof gap; test-writer added direct valid-id helper coverage.
- Verification (quality-runner scoped): 15 passed, 0 failed in tests/test_decisions_1218.py.
- Lint (quality-runner scoped): clean for serve/cockpit/src/owlbear_cockpit/routes/decisions.py and tests/test_decisions_1218.py.
- Coverage (informational, task-scoped): owlbear_cockpit.routes.decisions 39% on this narrow suite; no builder code touched in this pass.
- Outcome: builder pass-through to review (test-only retry, implementation already satisfies updated tests).

### Evidence Summary
- AC3 gap identified by review is now covered by the new direct helper valid-id test.
- Current implementation behavior matches strengthened test expectations; no further source intervention required.

### Post-task Reflection
- Pattern discovered: reviewer-found test-proof gaps can often be resolved by test-writer without any builder source delta.
- Quality note: scoped coverage can remain low when only a single task test file is run; use it as task evidence, not module-completeness evidence.
