---
id: 1370
title: 'P1-07: Test Cockpit backend error envelope and guidance contract'
status: in-progress
priority: critical
created: 2026-05-06T00:58:41.555448+00:00
updated: 2026-05-06T05:08:54.631987+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-api
- type:test
- backend
- interface-contract
- guidance
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write backend tests that define the Cockpit error envelope and kanban guidance policy before implementation.

## Problem Evidence
- Cockpit mutation routes mostly return plain HTTPException detail strings, while kanban errors expose code and user_message.
- CockpitView clears guidance implicitly; the list route passes guidance on cache miss but drops it on cache hit.
- Frontend code currently branches on status codes and generic strings inconsistently.

## Acceptance Criteria
- Tests assert error responses use a JSON envelope with fields `code` (non-empty `str`, stable machine-readable identifier) and `message` (non-empty `str`, user-facing explanation), and assert `detail` is absent — for ALL representative error categories (404, 409, 422, 500), not just the 404 shape tests. (td:2)
- Tests cover representative expected errors: not-found (404), stale/conflict (409), validation (422), invalid-config (500), and unhandled scanner/repair exceptions (500). Each asserts both status code and envelope fields. (td:2)
- Tests assert HTTP status codes are unchanged — the envelope wraps existing semantics without altering status mapping. (td:1)
- Tests assert guidance policy: (a) error responses do NOT include a `guidance` field; (b) successful list responses include engine guidance on cache miss (proved via non-empty sentinel mock) and return `guidance: []` on cache hit (cache-hit test must seed via a miss with non-empty sentinel guidance, then assert hit returns `[]`); (c) successful mutation responses return `guidance: []` (no operation-level guidance exists for mutations). (td:2)
- At least one test per category (envelope shape, error coverage, status preservation, guidance policy) fails against the current unmodified routes — proving the RED phase is valid for #1371. (td:1)

## Scope
- In scope: Cockpit backend API contract tests for expected errors and guidance handling.
- Out of scope: frontend UI adoption, dashboard redesign, cache/SSE invalidation from #1346, and health-endpoint false-OK logic (belongs to #1372).

## Architecture Notes
- **Envelope shape**: `{"code": "<STABLE_CODE>", "message": "<user-facing text>"}`. Codes should mirror kanban error codes where applicable (e.g., `ERR_NOT_FOUND`, `ERR_STALE`, `ERR_INVALID_STATUS`) and use Cockpit-specific codes for non-kanban errors (e.g., `COCKPIT_CONFIG_ERROR`, `COCKPIT_SCANNER_FAILED`).
- **Implementation target**: A custom FastAPI exception handler or middleware in `serve/cockpit/src/owlbear_cockpit/` that catches `KanbanError` subclasses and unhandled route exceptions, serializing them into the envelope.
- **Test file**: `tests/test_cockpit_error_envelope_1370.py` — use existing DI pattern (`get_engine` override) to inject engine mocks that raise specific errors.
- **Guidance contract**: The current cache-hit behavior (`guidance: []`) is correct — guidance reflects the engine query that produced the response; no stale guidance should be surfaced. Tests document this as contract, not as a bug.
- **Scanner/repair scope**: Test that when `view.scan_corruption()` or `view.repair_storage()` raises an unexpected exception, the response uses the error envelope with 500 status and a stable code rather than FastAPI's generic error page.

## Counterpart
Implementation task: #1371.
[[2026-05-06]]
## Architecture Review (retry)

**Verdict: REFINE → approve**

Addressed two reviewer-identified false-green proof gaps:

1. **AC1 tightened:** Non-empty `str` assertions + `detail` absence required for ALL representative error categories (409/422/500), not just 404. Previously only 404 path had type/value checks.

2. **AC4(b) tightened:** Cache-hit test must seed via mocked miss with non-empty sentinel guidance, then assert hit returns `[]`. Previously the cache was warmed with a live miss that returned `[]`, making the assertion trivially true.

AC body replaced with refined wording. Test-writer instructions appended for the two specific code changes needed. No architectural changes — same envelope shape, same patterns, same test infrastructure.
[[2026-05-06]]
## Test-Writer Notes
- Test file: tests/test_cockpit_error_envelope_1370.py
- Classes: TestFromAC_ErrorEnvelopeShape, TestFromAC_ErrorCoverage, TestFromAC_StatusPreservation, TestFromAC_GuidancePolicy
- Tests per category: happy 4, edge 5, error 8, boundary 5
- Total: 22 tests, all FAIL
- ruff: clean

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 (td:2) – envelope shape {code, message}, no detail, non-empty str, all error categories | TestFromAC_ErrorEnvelopeShape (9 tests) — covers 404, 409, 422, 500 with isinstance+non-empty str assertions; tightened per arch-review |
| AC2 (td:2) – representative errors: 404, 409, 422, 500-config, 500-scanner, 500-repair | TestFromAC_ErrorCoverage (6 tests) |
| AC3 (td:1) – HTTP status codes unchanged | TestFromAC_StatusPreservation (3 tests) |
| AC4 (td:2) – guidance policy: no guidance on errors, sentinel-seeded cache-hit=[], mutation=[] | TestFromAC_GuidancePolicy (4 tests) — cache-hit test seeds via mocked miss with non-empty sentinel; tightened per arch-review |

**Arch-review tightening applied:**
1. Added 3 new isinstance+non-empty-string tests for 409/422/500 envelope shape (AC1)
2. Fixed cache-hit test to seed via mocked miss with sentinel guidance (AC4b)