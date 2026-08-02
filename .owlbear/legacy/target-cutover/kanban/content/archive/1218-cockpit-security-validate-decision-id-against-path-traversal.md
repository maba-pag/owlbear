---
id: 1218
title: Cockpit security — validate decision_id against path traversal
status: archived
priority: medium
created: 2026-04-30 16:31:07.651363+00:00
updated: 2026-04-30T22:42:42.921028+00:00
tags:
- cockpit
- security
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
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

[[2026-04-30]]
## Review Evidence

### Scope
- Reviewed the live task-owned source and tests in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py) and [tests/test_decisions_1218.py](tests/test_decisions_1218.py).
- Builder commit presence for the original source change was confirmed in [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L1104); changed-file scope for this review was reconstructed from the task body plus the live files because reviewer tools do not expose direct git diff.

### Test Results
- quality-runner scoped pytest: 15 passed, 0 failed in [tests/test_decisions_1218.py](tests/test_decisions_1218.py)

### Lint
- quality-runner scoped ruff: clean for [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py) and [tests/test_decisions_1218.py](tests/test_decisions_1218.py)

### Coverage
- quality-runner explicit module rerun produced 39% coverage for [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py).
- This is informational, not a reject reason. The review gate is diff-scoped changed behavior, and the changed validation path in [_find_decision_path](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L94) is directly exercised by exact helper and route assertions in the task-owned suite.

### Pass 1 - Critical

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: helper raises HTTP 422 for malformed ids before Path.exists or filesystem lookup | [test_invalid_id_raises_http422](tests/test_decisions_1218.py#L125), [test_no_filesystem_io_for_traversal_payload](tests/test_decisions_1218.py#L192), [test_no_filesystem_io_for_empty_id](tests/test_decisions_1218.py#L211) against the allowlist gate at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96) and the first lookup at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L100) | Yes | COVERED |
| AC2: resolve route returns HTTP 422 for malformed ids | [test_route_422_for_dot_hidden_id](tests/test_decisions_1218.py#L231) and [test_route_422_for_dot_dot_traversal_id](tests/test_decisions_1218.py#L242), with the route only remapping FileNotFoundError at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L151) | Yes | COVERED |
| AC3: direct helper coverage includes traversal payloads and a valid allowlisted id | Direct bad-id helper coverage at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L125) and direct valid-id success proof at [test_valid_id_returns_pending_path](tests/test_decisions_1218.py#L164) with the exact returned-path assertion at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L181) | Yes | COVERED |

#### Security Review
- PASS: the allowlist in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L19) blocks traversal-shaped ids before any path existence checks in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L100). No new injection, path traversal, or secret-handling issue was introduced in scope.

#### Test Integrity
- PASS: the live TestFromAC suite preserves the earlier negative-path assertions and strengthens AC3 with an exact success-path assertion in [test_valid_id_returns_pending_path](tests/test_decisions_1218.py#L164-L181). No weakened or removed TestFromAC assertions found.

#### Test Quality
- PASS: assertions are exact HTTP status codes or exact returned path values, not loose truthiness checks. The precondition-order tests patch the actual call site with [Path.exists monkeypatch setup](tests/test_decisions_1218.py#L200) and [zero-call assertion](tests/test_decisions_1218.py#L206), repeated for empty-id at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L219-L223).

#### Data Safety
- PASS: malformed ids are rejected in the helper before file lookup in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L100), and no shared-state or write-path regression appears in the changed behavior.

#### Implementation-Aware Test Gaps
- PASS for AC scope: no remaining AC-blocking gaps. The resolved-file compatibility branch at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L103) and valid-missing-id 404 behavior are not exercised by this task suite, but those branches are outside AC 1-3 and are informational only.

#### Builder Process Quality
- CLEAN: one prior review reject for a test-proof gap, then a test-only retry that added the missing valid-id helper proof, followed by a builder pass-through with no source delta. No loop pattern detected.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Helper validation fires before the first path lookup in [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L96-L100), and the suite asserts no Path.exists calls for malformed ids at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L192-L223) | invalid-id helper tests and no-filesystem-io tests | PASS |
| AC2 | The route resolves through the helper at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L142-L164) and only converts FileNotFoundError at [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L151); malformed-id route tests assert 422 at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L231-L250) | route 422 tests | PASS |
| AC3 | The suite directly calls _find_decision_path for the required malformed payloads at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L125-L162) and for the valid allowlisted id at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L164-L181) | direct helper tests | PASS |

### Informational
- The default quality-runner coverage report initially omitted cockpit module-level coverage; an explicit module-targeted rerun produced the needed evidence without changing the verdict.
- The route test label at [tests/test_decisions_1218.py](tests/test_decisions_1218.py#L242) overstates the payload as URL-decoded traversal, but the assertion still correctly proves malformed-id 422 behavior.

### Deductions
- -0.02 changed-file scope reconstructed from task notes plus commit-presence evidence instead of a direct git diff
- -0.01 initial default coverage report required explicit cockpit-module rerun
- Confidence: 0.97

### Verdict
- PASS -> docs. The prior AC3 proof gap is closed, the live implementation satisfies all three AC lines, and the strengthened task-owned suite is now discriminating enough to catch regressions in the validation path.

### Post-task Reflection
- Default scoped coverage on cockpit routes was noisy; explicit module-targeted coverage produced the usable evidence.
- The prior reject was resolved cleanly by a test-only retry, with no source change needed in the second builder pass.
- For narrow security tasks, low whole-module coverage is informational when the AC-mapped changed path is directly exercised by exact assertions.
[[2026-04-30]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` Decisions API table line for `POST /api/decisions/{id}/resolve` said "Returns 404 for unknown ids" — now correctly states 422 for malformed ids (allowlist pattern) and 404 for valid-but-unknown ids |
| 2 | Module docstrings | Yes | Updated | `_find_decision_path()` docstring expanded to document the allowlist validation, 422 raise, and FileNotFoundError raise |
| 3 | External attribution | No | N/A | No external repo patterns cited; OWASP allowlist is general security knowledge |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**`; matches changed file. Footer updated from `2026-04-30 (9cf3a3b7)` to `2026-05-01 (358f5aaf)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` | IN (docstring) | Updated `_find_decision_path()` docstring |
| `tests/test_decisions_1218.py` | OUT | N/A |
| `serve/cockpit/README.md` | IN | Updated Decisions API table |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/cockpit/README.md` — Decisions API 422 behavior documented
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` — `_find_decision_path()` docstring updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `2026-05-01 (358f5aaf)`

### Commit
- `f584b298` — docs: update decisions API docs and diagram for path traversal validation (#1218, doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files found for task 1218)
[[2026-04-30]]
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `_find_decision_path()` raises HTTPException(422) for invalid ids before filesystem I/O | Allowlist at decisions.py:L19 (`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`), guard at L101-102; test_invalid_id_raises_http422 (5 parametrize cases) + 5 explicit per-payload; no-I/O assertions via Path.exists spy in TestFromAC_ValidationBeforeFilesystemIO | PASS |
| AC2: resolve route returns 422 for malformed ids | Route remaps only FileNotFoundError at L151; HTTPException(422) propagates from helper; test_route_422_for_dot_hidden_id + test_route_422_for_dot_dot_traversal_id confirm 422 | PASS |
| AC3: direct helper tests cover all traversal payloads and a valid id like 1234-some-slug | Traversal payloads: parametrize + 5 explicit tests; valid-id: test_valid_id_returns_pending_path creates file and asserts correct path returned without exception. Test present and passing. Process note: this retry test is in working tree only (uncommitted) | PASS (functional) |

### Test Results
- Scoped pytest (quality-runner): 15 passed, 0 failed — clean
- Full suite (q1222 prior run, same day): 129 failed, 3340 passed, 4 skipped — no decisions-related failures; background debt outside 1218 scope
- Lint: ruff clean for decisions.py and test_decisions_1218.py

### Commits
- 5caa65d3: test-writer RED phase (14 tests)
- 4f50ce0a: builder implementation (decisions.py allowlist + pre-I/O guard)
- f584b298: doc-writer docs (README, docstring, diagram)
- Process gap: test-writer retry (test_valid_id_returns_pending_path) is uncommitted working-tree modification. Test runs and passes but is absent from git history. Noted as process concern; not blocking given security fix is committed and test functions correctly.

### Architect Quality: 4/5
Exact allowlist pattern specified, HTTPException type specified, "before filesystem I/O" structurally provable, unit-level testing required explicitly. AC3 positive-case requirement was tight enough to catch the test-coverage gap at first review. Minor: architecture notes could have clarified that "valid id" means one that exists on disk (triggering the success branch), not just one that passes the regex.

### Deduction Breakdown
- -0.02 uncommitted test deliverable (retry test in working tree only)
- -0.01 full-suite evidence from prior audit run (same day, no decisions failures, but not a fresh run)

### Confidence: 0.97
### Action: archive