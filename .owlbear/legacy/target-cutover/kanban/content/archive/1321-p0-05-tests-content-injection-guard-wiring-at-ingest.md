---
id: 1321
title: 'P0-05: Tests — Content injection guard wiring at ingest'
status: archived
priority: medium
created: 2026-05-04T05:48:37.782310+00:00
updated: 2026-05-04T10:20:54.072536+00:00
tags:
- phase-0
- scope:knowledge
- knowledge
- test
parent: 1316
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.6)

## Acceptance Criteria

- [ ] Tests verify ContentInjectionGuard is instantiated in app_lifespan and passed to IngestPipeline; `scan()` is called during `ingest_text()` flow (td:2)
- [ ] Tests verify content with injection markers is blocked (not stored) in strict mode, and threat-flagged with warning in non-strict mode, before chunk storage (td:2)
- [ ] Tests verify guard `scan()` completes before `store_chunks()` is called — ordering assertion (td:2)
- [ ] Tests verify search/query path does not invoke guard on pre-existing chunks (D20: ingest-only guard) (td:2)
- [ ] Tests verify guard runs for all `source_type` metadata values passed to `ingest_text()` — no content type is exempted from scanning (td:2)

## Scope

- **In scope:** Guard wiring tests at `ingest_text()` entry point (used by `ingest_document` and `bookmark_source` MCP tools), block/flag behavior, ordering, D20 compliance
- **Out of scope:** Guard at enrichment time (D20 — ingest only), guard implementation changes, `ingest()` method (already has guard support — ordering fix is implementation concern for #1322)

## Builder Notes

- Current `ingest()` in `serve/knowledge/src/owlbear_knowledge/ingest.py` calls `store_chunks()` BEFORE `content_guard.scan()` (L220 vs L224) — this is a known defect. AC3 tests define desired behavior; #1322 must fix ordering.
- `ingest_text()` currently has zero guard logic — guard wiring is the primary implementation target for #1322.
- `app_lifespan` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` does not import or instantiate `ContentInjectionGuard` — #1322 must add this.
- Guard API: `ContentInjectionGuard.scan(text) → CheckResult(threat: bool, blocked: bool, reason: str, pattern: str)`. `strict_mode=True` → `blocked=True` on match; `strict_mode=False` → `blocked=False, threat=True`.
- Test patterns: follow `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` (AsyncMock, MagicMock, `_make_app_context()` fixture pattern).
- Use `mock.call_args_list` index ordering or a call-tracker for AC3 ordering assertions (no `assert_called_before` helper exists in repo).

## Research

**Key findings:**
- ContentInjectionGuard fully implemented (~40 patterns, `scan()` → `CheckResult`)
- Two gaps: (1) `app_lifespan` doesn't instantiate/pass guard to pipeline, (2) `ingest_text()` has zero guard logic despite `ingest()` having it
- MCP tool calls `ingest_text()` — the unguarded path
- AC5 tension: AC says "all content types" but existing `ingest()` only guards untrusted. Recommendation: guard ALL content unconditionally in `ingest_text()` (confidence 0.75)
- D20: guard at ingest only, pre-guard legacy chunks accepted

**Test architecture:** 5 test classes in `tests/test_content_guard_wiring_1321.py` mapping 1:1 to AC lines. Mock-based, following patterns from `test_ingest_graph_tools.py`.

**Doc:** `.owlbear/research/content-guard-wiring-tests.md`
**Follow-ups:** #1322 already exists (implementation, depends on #1321)
[[2026-05-04]]
## Architecture Review

### Verdict: APPROVED (after REFINE)

All 5 AC lines refined for precision. Challenger invoked — 3 critical concerns addressed.

### AC Assessment

| AC | Original | Assessment | Action |
|----|----------|-----------|--------|
| AC1 | "Guard invoked during ingest_document flow" | Imprecise — doesn't specify where guard is instantiated | Refined: explicit `app_lifespan` + `ingest_text()` path |
| AC2 | "rejected or sanitized" | Guard has no sanitization API — only block/warn | Refined: "blocked in strict mode, threat-flagged in non-strict mode" |
| AC3 | "Guard runs before chunk storage" | Correct intent; existing `ingest()` has store-before-scan defect (L220 vs L224) | Kept + added Builder Note documenting the defect |
| AC4 | "Pre-guard legacy chunks accepted (D20)" | Testable via query path verification | Refined: "search/query path does not invoke guard" |
| AC5 | "All content types (local files, URLs, browser-fetched)" | Over-broad — spans multiple ingestion seams | Refined: scoped to `source_type` metadata variants in `ingest_text()` |

### Architecture Notes

- `ingest_text()` is the common funnel for both `ingest_document` and `bookmark_source` MCP tools — correct test target
- Guard wiring is constructor-level + method-level change in #1322; no new interfaces needed
- Existing `ingest()` guard support proves the pattern; `ingest_text()` just needs the same treatment
- Store-before-scan ordering defect documented as Builder Note for #1322

### Dependency Analysis

- No upstream dependencies (Layer 0 foundation task)
- #1322 (implementation) correctly depends on #1321
- No missing dependencies detected

### Challenger Results

- Confidence: 0.38 → re-evaluated and addressed all 3 critical concerns
- AC2 sanitization ambiguity: FIXED (rewritten to block/flag semantics)
- AC3 ordering defect: ACKNOWLEDGED (Builder Note added; tests define desired behavior)
- AC5 scope conflation: FIXED (scoped to `source_type` metadata, not code paths)
- Override rationale: concerns were valid refinement triggers, not blockers. All addressed in body edit.

### Test Depth

- All lines: td:2 (multiple paths, ordering, parameterized)
- Test-writer: PROCESS (standard TDD RED)
[[2026-05-04]]
## Test-Writer Notes

**File:** `tests/test_content_guard_wiring_1321.py`
**Total:** 29 tests — 25 FAIL ✓ / 4 pass (regression guards, see below)
**Lint:** ruff clean ✓

### Test classes

| Class | AC | Tests | Category breakdown |
|---|---|---|---|
| `TestFromAC_LifespanGuardWiring` | AC1 | 5 | happy(1), edge(2), boundary(2) |
| `TestFromAC_BlockAndWarnBehavior` | AC2 | 7 | happy(2), edge(3), error(1), regression(1) |
| `TestFromAC_ScanOrdering` | AC3 | 3 | happy(1), ordering(1), boundary(1) |
| `TestFromAC_SearchPathNoGuard` | AC4 | 3 | regression guards (see below) |
| `TestFromAC_AllSourceTypesScanned` | AC5 | 11 | parametrized(9) + edge(2) |

### AC coverage

| AC | Tests | Fail status |
|---|---|---|
| AC1 — Guard instantiated in lifespan, scan() called in ingest_text() | 5 | ALL FAIL ✓ |
| AC2 — Block in strict mode, warn in non-strict mode, before storage | 7 | 6 FAIL ✓, 1 regression guard |
| AC3 — scan() before store_chunks() ordering | 3 | ALL FAIL ✓ |
| AC4 — Search path does NOT invoke guard (D20) | 3 | regression guards (pass — see below) |
| AC5 — All source_type values trigger scan, no exemptions | 11 | ALL FAIL ✓ |

### Regression guards (4 passing — by design)

Three `TestFromAC_SearchPathNoGuard` tests verify D20: search path must NOT call guard. Since search never calls guard (now or after #1322), "not called" assertions trivially pass and cannot be made to fail without inverting the contract. These are valid regression guards ensuring #1322 doesn't accidentally wire guard into the query path.

`test_no_guard_allows_injection_text_through` similarly tests guard=None passthrough — correct before and after implementation.

### Failure modes

Primary: `AssertionError` — `guard.scan.assert_called()` fails because `ingest_text()` has zero guard logic. Secondary: `AssertionError` — `result.status == "blocked"` fails because `ingest_text()` returns "ok" unconditionally.
[[2026-05-04]]
## Builder Notes
- Files changed: serve/knowledge/src/owlbear_knowledge/ingest.py; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Implementation summary:
  - Added `ContentInjectionGuard` instantiation in `app_lifespan` and passed it into `IngestPipeline` as `content_guard`.
  - Added guard scanning in `ingest_text()` before any persistence calls.
  - Enforced strict-mode blocking path (`status="blocked"`, zero entity/edge counts) before `store_chunks()`.
  - Added non-strict threat warning logging while allowing ingestion to proceed.
  - Scans run for every chunk with no `source_type` exemption in `ingest_text()`.
- RED verification (pre-change): quality-runner reported 25 failing `TestFromAC_*` tests and 4 expected regression passes in `tests/test_content_guard_wiring_1321.py`.
- GREEN verification (post-change):
  - Tests: 29 passed, 0 failed (`tests/test_content_guard_wiring_1321.py`)
  - Lint: ruff clean on changed files and task test
  - Coverage (scoped report):
    - `owlbear_knowledge.ingest`: 55%
    - `owlbear_mcp_knowledge.server`: 44%
    - overall scoped run: 31%
- Evidence summary:
  - AC1 satisfied via lifecycle guard wiring and guard type at pipeline construction.
  - AC2/AC3 satisfied via scan-before-store ordering and strict block/non-strict warning behavior.
  - AC4 remained intact (no query-path guard wiring added).
  - AC5 satisfied via unconditional scan loop in `ingest_text()` across all metadata/source_type values.
- Commit:
  - `cd74db6e2cd965b5b9c226e77336c829545a66f8` — feat: wire ingest guard at lifespan/text path (#1321, builder)
[[2026-05-04]]
## Review Evidence
### Test Results
- pytest: 29 passed, 0 failed (`tests/test_content_guard_wiring_1321.py`)

### Lint: clean
- `ruff check` clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`

### Coverage
- `owlbear_knowledge.ingest`: 55%
- `owlbear_mcp_knowledge.server`: 44%
- Module coverage is informational only here; the scoped task suite exercises the changed guarded path, but the report is not diff-scoped.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — Guard instantiated in `app_lifespan`, passed to `IngestPipeline`, and `scan()` called in `ingest_text()` | `test_app_lifespan_passes_content_guard_to_ingest_pipeline`, `test_content_guard_is_content_injection_guard_instance`, `test_ingest_text_calls_scan_on_guard`, `test_ingest_text_passes_chunk_text_to_scan`, `test_ingest_text_scans_every_chunk` | Yes — the assertions at `tests/test_content_guard_wiring_1321.py:149`, `:164`, `:178`, `:191`, and `:214` would fail if the guard were omitted, `None`, the wrong type, called with transformed text, or not called for every chunk | COVERED |
| AC2 — Strict block/not-store and non-strict warn path before chunk storage | `test_strict_mode_blocked_content_not_stored`, `test_non_strict_mode_does_not_block`, `test_non_strict_mode_logs_warning_on_threat` | No for the non-strict injected-content branch — strict proof is good (`tests/test_content_guard_wiring_1321.py:261`, `:272`), but the non-strict checks only assert `status != "blocked"` at `:303` and `warning.assert_called()` at `:316`; there is no non-strict `store_chunks` assertion anywhere in the file, so warn-plus-early-return or warn-without-store mutations would stay green | LAX |
| AC3 — `scan()` completes before `store_chunks()` | `test_scan_called_before_store_chunks`, `test_blocked_scan_prevents_store_chunks`, `test_multi_chunk_blocked_first_stops_before_second` | Yes — the call-log and blocked-path assertions at `tests/test_content_guard_wiring_1321.py:356`, `:390`, and `:426` would fail on reversed ordering or blocked persistence | COVERED |
| AC4 — Search/query path does not invoke guard | `test_search_knowledge_does_not_invoke_guard_scan`, `test_query_service_called_without_guard_in_call_chain`, `test_search_returns_results_containing_injection_text` | Yes — the search path at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:364-375` calls `qs.query(...)` directly, and the tests at `tests/test_content_guard_wiring_1321.py:473`, `:493`, and `:509` would fail if guard wiring leaked into query | COVERED |
| AC5 — All `source_type` values in `ingest_text()` are scanned | `test_guard_scans_for_source_type`, `test_trusted_source_types_are_not_exempt_in_ingest_text`, `test_absent_metadata_still_triggers_scan` | Yes — the unconditional scan path at `serve/knowledge/src/owlbear_knowledge/ingest.py:99-113` is exercised by the tests at `tests/test_content_guard_wiring_1321.py:559`, `:580`, and `:603` across trusted, untrusted, unknown, and absent metadata cases | COVERED |

#### Security Review
- No new in-scope issues found in the reviewed task paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suite described in the Test-Writer notes (5 classes, 29 tests) | Current file still contains the same 5 `TestFromAC_*` classes and no visible `skip`/`xfail` weakening; commit diff was not available in this tool surface | PRESERVED (lower-confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `tests/test_content_guard_wiring_1321.py:303` only asserts `status != "blocked"`; `:316` only asserts that a warning happened |
| Negative/error-path coverage | ADEQUATE | Strict blocked/not-stored is proven at `tests/test_content_guard_wiring_1321.py:261-272`; blocked ordering is covered at `:390-407` |
| Manual mutation reasoning | WEAK | A non-strict threat-path mutation that warns and returns `failed`, `skipped`, or `ok` before persistence would still satisfy the current AC2 assertions |
| Test independence | STRONG | Helpers build fresh pipelines/stores; no shared mutable fixture state is required |
| Naming | STRONG | Test names map directly to the AC language |

#### Data Safety
- No new in-scope issues found. The pre-existing `ingest()` ordering defect noted in the task body remains out of scope for 1321 and was not used as a gate.

#### Implementation-Aware Gaps
- No in-scope implementation miss found in the current `ingest_text()` path. Current source at `serve/knowledge/src/owlbear_knowledge/ingest.py:99-131` scans/warns before persistence, but the non-strict threat branch lacks discriminating proof of post-warning persistence/order.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A — one pre-build context section plus one actual builder section; no retry loop evidenced |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `code-reader` flagged the unchanged `ingest()` path at `serve/knowledge/src/owlbear_knowledge/ingest.py:242-249` for store-before-scan ordering. The task body explicitly marks `ingest()` out of scope, so I treated this as residual debt rather than a gating failure for 1321.
- Test integrity confidence is slightly reduced because commit diff / dirty-tree status was not available from the current tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:288-293` wires `ContentInjectionGuard()` into `IngestPipeline`; `serve/knowledge/src/owlbear_knowledge/ingest.py:99-101` calls `scan()` | `test_app_lifespan_passes_content_guard_to_ingest_pipeline` (`tests/test_content_guard_wiring_1321.py:149`), `test_content_guard_is_content_injection_guard_instance` (`:164`), `test_ingest_text_calls_scan_on_guard` (`:178`), `test_ingest_text_passes_chunk_text_to_scan` (`:191`), `test_ingest_text_scans_every_chunk` (`:214`) | PASS |
| AC2 | Source behavior is present at `serve/knowledge/src/owlbear_knowledge/ingest.py:99-131`, but the non-strict proof is lax: strict blocking/not-stored is proven at `tests/test_content_guard_wiring_1321.py:261`/`:272`, while non-strict injected-content checks at `:291`, `:303`, `:308`, and `:316` do not assert exact success/persistence/order | `test_strict_mode_blocked_content_not_stored`, `test_non_strict_mode_does_not_block`, `test_non_strict_mode_logs_warning_on_threat` | FAIL |
| AC3 | `serve/knowledge/src/owlbear_knowledge/ingest.py:99-131` scans before store; ordering/assert-no-store proofs at `tests/test_content_guard_wiring_1321.py:356`, `:390`, and `:426` would fail on reversed ordering or blocked persistence | `test_scan_called_before_store_chunks`, `test_blocked_scan_prevents_store_chunks`, `test_multi_chunk_blocked_first_stops_before_second` | PASS |
| AC4 | Query path at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:364-375` calls `qs.query(...)` directly; no guard hook is present | `test_search_knowledge_does_not_invoke_guard_scan` (`tests/test_content_guard_wiring_1321.py:473`), `test_query_service_called_without_guard_in_call_chain` (`:493`), `test_search_returns_results_containing_injection_text` (`:509`) | PASS |
| AC5 | `serve/knowledge/src/owlbear_knowledge/ingest.py:99-113` scans unconditionally once chunks exist; tests cover present/absent and trusted/untrusted `source_type` variants | `test_guard_scans_for_source_type` (`tests/test_content_guard_wiring_1321.py:559`), `test_trusted_source_types_are_not_exempt_in_ingest_text` (`:580`), `test_absent_metadata_still_triggers_scan` (`:603`) | PASS |

### Confidence: 0.84
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the AC2 non-strict injected-content proof to assert an exact successful outcome and real persistence after the warning, not just `status != "blocked"` | `tests/test_content_guard_wiring_1321.py` | Test Quality — assertion specificity WEAK; `tests/test_content_guard_wiring_1321.py:303` |
| 2 | test-writer | Add a non-strict threat-path ordering/persistence check proving injected content with `blocked=False, threat=True` reaches `store_chunks()` only after scan/warning | `tests/test_content_guard_wiring_1321.py` | AC2 coverage is LAX; `tests/test_content_guard_wiring_1321.py:291-316`, with no non-strict `store_chunks` assertion anywhere in the file |
[[2026-05-04]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.

### New tests added to `TestFromAC_BlockAndWarnBehavior`

| Test | Addresses | Status |
|------|-----------|--------|
| `test_non_strict_mode_returns_ok_status_on_threat` | Follow-up #1: assert exact `status == "ok"`, not just `!= "blocked"` | PASS ✓ |
| `test_non_strict_threat_content_reaches_store_chunks` | Follow-up #2: ordering + persistence — scan → warning → store_chunks for non-strict threat content | PASS ✓ |

### Rationale for direct-to-review
Both tests pass against the current implementation (`ingest_text()` already persists non-strict threat content and returns `"ok"`). Implementation satisfies the stricter proof — builder has no work to do.

### Lint
- `ruff check tests/test_content_guard_wiring_1321.py` — clean ✓

### Total: 31 tests, all pass (29 prior + 2 new)
[[2026-05-04]]
## Builder Notes
- No code changes in this builder pass (test-only retry validated against existing implementation).
- Verification rerun via quality-runner (scoped):
  - `uv run pytest tests/test_content_guard_wiring_1321.py --cov=owlbear_knowledge.ingest --cov=owlbear_mcp_knowledge.server --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
  - `uv run ruff check serve/knowledge/src/owlbear_knowledge/ingest.py serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_content_guard_wiring_1321.py`
- Results:
  - Tests: 31 passed, 0 failed
  - Coverage: `owlbear_knowledge.ingest` 55%, `owlbear_mcp_knowledge.server` 44%
  - Lint: clean (0 issues)
- Evidence summary:
  - AC1/AC3/AC4/AC5 remain satisfied by existing implementation and passing `TestFromAC_*` suite.
  - AC2 strengthened proofs from test-writer retry are passing (`status == "ok"` in non-strict threat mode plus non-strict threat persistence/order assertion).
- Builder verdict: no further implementation required for #1321; ready for review.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner (scoped): 31 passed, 0 failed for `tests/test_content_guard_wiring_1321.py`

### Lint Results
- `ruff check` clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`

### Coverage
- `owlbear_knowledge.ingest`: 55%
- `owlbear_mcp_knowledge.server`: 44%
- Module percentages are informational only here; the gate is AC proof quality on the changed guarded path.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — Guard instantiated in `app_lifespan`, passed to `IngestPipeline`, and `scan()` called during `ingest_text()` | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:288-293` instantiates `ContentInjectionGuard()` and passes it into `IngestPipeline`; `serve/knowledge/src/owlbear_knowledge/ingest.py:105-115` scans each chunk before persistence | `tests/test_content_guard_wiring_1321.py:149`, `:178` | PASS |
| AC2 — Injection content is blocked (not stored) in strict mode, and threat-flagged with warning in non-strict mode, before chunk storage | Implementation behavior exists at `serve/knowledge/src/owlbear_knowledge/ingest.py:105-115` and `:136-142`. Strict no-store is proven at `tests/test_content_guard_wiring_1321.py:261` and `:272`. Exact non-strict status is now proven at `tests/test_content_guard_wiring_1321.py:335` and `:346`. Non-strict persistence/order is only partially proven at `tests/test_content_guard_wiring_1321.py:352`, `:387`, and `:393`: that retry records `scan` and `store_chunks`, but it does not record `logger.warning`, and the only executable warning assertion remains `mock_logger.warning.assert_called()` at `tests/test_content_guard_wiring_1321.py:316`. A mutation that moves warning after storage would still pass. | `tests/test_content_guard_wiring_1321.py:261`, `:308`, `:316`, `:335`, `:352` | FAIL |
| AC3 — `scan()` completes before `store_chunks()` | `serve/knowledge/src/owlbear_knowledge/ingest.py:105-115` scans before persistence, and the call-order proof at `tests/test_content_guard_wiring_1321.py:420` and `:449` would fail on reversed ordering | `tests/test_content_guard_wiring_1321.py:420` | PASS |
| AC4 — Search/query path does not invoke guard on pre-existing chunks | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:375` calls `qs.query(...)` directly; `serve/knowledge/src/owlbear_knowledge/query_service.py:85` exposes no guard parameter on `query(...)`; class-level patching at `tests/test_content_guard_wiring_1321.py:551` with `mock_scan.assert_not_called()` at `:554` would fail if the query path invoked `ContentInjectionGuard.scan()` | `tests/test_content_guard_wiring_1321.py:537`, `:554`, `:557`, `:569`, `:570` | PASS |
| AC5 — All `source_type` values passed to `ingest_text()` are scanned | `serve/knowledge/src/owlbear_knowledge/ingest.py:105-115` scans unconditionally once chunks exist; parametrized coverage at `tests/test_content_guard_wiring_1321.py:623` exercises the source-type matrix | `tests/test_content_guard_wiring_1321.py:623` | PASS |

### Pass 1 — Critical Checks
- Test-Writer AC coverage: FAIL on AC2 only. The retry closed the prior exact-status/persistence gap, but it still does not execute an assertion for the AC text "warning ... before chunk storage."
- Security/Data safety: code-reader flagged the sibling `ingest()` path at `serve/knowledge/src/owlbear_knowledge/ingest.py:251-260` for store-before-scan behavior, but the task body explicitly marks `ingest()` out of scope for 1321, so this was not used as a gate here.
- Test integrity: no visible weakening in the current `TestFromAC_*` snapshot. Confidence is slightly reduced because direct git diff / dirty-tree commands were not available in this tool surface.

### Deductions
- `-0.10` AC2 remains under-proven on the warning-before-storage clause.
- `-0.03` Test-integrity confidence reduced because direct git diff / dirty-tree contamination checks were unavailable. The builder commit hash `cd74db6e2cd965b5b9c226e77336c829545a66f8` is present in `.git/logs/refs/heads/dev` and `.git/logs/HEAD`, but changed-file and overlap checks could not be executed here.

### Verdict
- Confidence: 0.87
- FAIL
- Route: `backlog` under the loop-breaker rule. This task already contains a prior `## Review Evidence` failure (`.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md:162`), so a second review failure must not go back to a direct retry lane.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC2 wording with executable proof expectations. If "warning ... before chunk storage" is binding, require a test that records `logger.warning` in the same order trace as `store_chunks`; if that ordering is not intended to gate the task, narrow the AC text accordingly before redispatch. | `.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md`, `tests/test_content_guard_wiring_1321.py` | AC2 says warning occurs before chunk storage, but current retry only proves warning occurrence at `tests/test_content_guard_wiring_1321.py:316` and scan/store ordering at `:352-393` without warning order in the trace. |
| 2 | architect | Apply the loop-breaker rule for this second review failure and re-plan the next owner instead of returning directly to builder. | `.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md` | Prior `## Review Evidence` exists at `.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md:162`; current review is another FAIL on task proof quality. |
[[2026-05-04]]


## Architecture Review (Loop-Breaker)

### Context

Second review failure routed task back to backlog under the loop-breaker rule. Both review failures cited AC2 — the phrase "before chunk storage" in the non-strict clause creates ambiguity that tests cannot prove (warning-before-store ordering vs scan-before-store ordering).

### AC2 Refinement

**Original AC2:** "Tests verify content with injection markers is blocked (not stored) in strict mode, and threat-flagged with warning in non-strict mode, before chunk storage (td:2)"

**Refined AC2:** "Tests verify content with injection markers is blocked (not stored) in strict mode; in non-strict mode, threat content triggers a warning log and is still persisted via `store_chunks()` (td:2)"

**Rationale:**
- "before chunk storage" conflated two concerns: (a) threat detection behavior (block vs warn), and (b) ordering (scan before store)
- AC3 already covers ordering: "`scan()` completes before `store_chunks()` is called"
- Warning is emitted inside the scan loop (`ingest.py:114-115`); it cannot drift to after storage without restructuring the scan loop, which would break AC3
- Warning is an observability concern (logging), not a security boundary — the security boundary is scan-before-store (AC3)
- The refined AC2 focuses on behavior: strict blocks, non-strict warns + persists

### Existing Evidence Satisfies Refined AC2

| Proof requirement | Test | Status |
|---|---|---|
| Strict: blocked, not stored | `test_strict_mode_blocked_content_not_stored` (L261) | PROVEN |
| Strict: status="blocked" | `test_strict_mode_blocked_result_has_zero_entity_and_edge_counts` (L272) | PROVEN |
| Non-strict: warning logged | `test_non_strict_mode_logs_warning_on_threat` (L316) | PROVEN |
| Non-strict: status="ok" | `test_non_strict_mode_returns_ok_status_on_threat` (L335) | PROVEN |
| Non-strict: content persisted | `test_non_strict_threat_content_reaches_store_chunks` (L352) | PROVEN |
| Non-strict: scan before store | `test_non_strict_threat_content_reaches_store_chunks` call_log (L393) | PROVEN |

All 31 tests pass. No new test work required.

### Challenger Results

- Verdict: `reconsider` at confidence 0.74
- Key concern: refinement is a deliberate scope narrowing, not implied by AC3
- Architect override: ACCEPTED. Warning is observability, not a security boundary. Warning lives inside the scan loop — AC3 (scan-before-store) implicitly guards warning ordering. Separating behavior (AC2) from ordering (AC3) is the correct decomposition.

### Evaluation (unchanged from first review)

| Criterion | Assessment |
|---|---|
| Single responsibility | PASS — test-only task |
| Interface clarity | PASS — AC refined for precision |
| Dependency correctness | PASS — no upstream deps, #1322 depends on this |
| Module layering | PASS — tests only, no production imports |
| TDD compliance | PASS — tests written first, builder verified |
| KISS/YAGNI | PASS — no over-engineering |
| Premise challenge | PASS — guard wiring tests are necessary for security |
| Pattern consistency | PASS — follows test_ingest_graph_tools.py patterns |
| Security surface | PASS — no new boundaries |
| Single domain | PASS — knowledge domain only |

### Test Depth

All lines td:2. Test-writer: PROCESS (standard TDD RED — already completed).

### Verdict: APPROVED (REFINE-then-APPROVE loop-breaker)

AC2 narrowed to remove ordering ambiguity (ordering is AC3's domain). Existing 31 tests satisfy all refined AC. No implementation or test changes required — straight pass-through to review.

[[2026-05-04]]
## Architecture Review (Loop-Breaker)

REFINE-then-APPROVE: AC2 narrowed to remove "before chunk storage" ambiguity — ordering is AC3's domain. Refined AC2: "Tests verify content with injection markers is blocked (not stored) in strict mode; in non-strict mode, threat content triggers a warning log and is still persisted via store_chunks()." Existing 31 tests satisfy all refined AC. Challenger overridden (0.74 reconsider → override: warning is observability, not security boundary; AC3 implicitly guards warning ordering). No code/test changes needed — pass-through to review.
[[2026-05-04]]
## Test-Writer Notes
- Architect loop-breaker (second review failure) refined AC2 to remove ordering ambiguity — "before chunk storage" was AC3's domain. Refined AC2: strict blocks (not stored); non-strict warns + persists.
- All 31 existing tests satisfy the refined AC. No new tests needed.
- Verification: `uv run pytest tests/test_content_guard_wiring_1321.py` → 31 passed, 0 failed. `ruff check` — clean.
- Pass-through to review (architect loop-breaker verdict: no code or test changes required).
[[2026-05-04]]
## Builder Notes
- No code changes in this builder cycle; this is a test-only pass-through after architect loop-breaker AC refinement.
- Verification rerun (scoped):
  - `uv run pytest tests/test_content_guard_wiring_1321.py --cov=owlbear_knowledge.ingest --cov=owlbear_mcp_knowledge.server --cov-report=term-missing --cov-fail-under=0 -v --tb=short`
  - `uv run ruff check serve/knowledge/src/owlbear_knowledge/ingest.py serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_content_guard_wiring_1321.py`
- Results:
  - Tests: 31 passed, 0 failed, 0 skipped
  - Coverage: `owlbear_knowledge.ingest` 55%, `owlbear_mcp_knowledge.server` 44% (overall scoped: 31%)
  - Lint: clean (0 issues)
- Evidence summary:
  - Refined AC2 behavior remains satisfied by existing implementation and strengthened tests (`status == "ok"` in non-strict threat mode plus non-strict threat persistence proof).
  - AC1/AC3/AC4/AC5 remain green in `TestFromAC_*` suite.
- Commit:
  - None (no files modified in this builder pass).
[[2026-05-04]]
## Review Evidence

### Test Results
- quality-runner scoped: 31 passed, 0 failed, 0 skipped for `tests/test_content_guard_wiring_1321.py`

### Lint Results
- Scoped lint confirmation: clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`
- The first parallel quality-runner report mentioned UP017 at `serve/knowledge/src/owlbear_knowledge/ingest.py:139`, but targeted lint-only rerun cleared it. The live line is `datetime.now(tz=UTC)`, so I did not treat lint as a gate.

### Coverage
- `owlbear_knowledge.ingest`: 52%
- `owlbear_mcp_knowledge.server`: 44%
- overall scoped run: 46%
- Informational only: this review gates on task AC proof and test safety, not module-wide percentages.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — guard instantiated in `app_lifespan`, passed to `IngestPipeline`, and `scan()` runs during `ingest_text()` | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:288-293`; `serve/knowledge/src/owlbear_knowledge/ingest.py:104-116` | `tests/test_content_guard_wiring_1321.py:149`, `:164`, `:178`, `:214` | PASS |
| AC2 — strict blocks/not stored; non-strict warns and persists | `serve/knowledge/src/owlbear_knowledge/ingest.py:104-116`, `:160-166`; reviewed against the loop-breaker refined AC2 in the task body | `tests/test_content_guard_wiring_1321.py:249`, `:261`, `:308`, `:335`, `:352` | PASS |
| AC3 — `scan()` completes before `store_chunks()` | `serve/knowledge/src/owlbear_knowledge/ingest.py:104-116`, `:165-168` | `tests/test_content_guard_wiring_1321.py:420`, `:490` | PASS |
| AC4 — search/query path does not invoke guard on pre-existing chunks | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:364-375` | `tests/test_content_guard_wiring_1321.py:537`, `:557`, `:573` | PASS |
| AC5 — all `source_type` values passed to `ingest_text()` are scanned | `serve/knowledge/src/owlbear_knowledge/ingest.py:104-106` | `tests/test_content_guard_wiring_1321.py:623`, `:644`, `:667` | PASS |

### Pass 1 — Critical Checks
#### Security/Data Safety
- FAIL: the task-local lifespan tests call `app_lifespan()` directly at `tests/test_content_guard_wiring_1321.py:153` and `:168`, but `app_lifespan()` unconditionally deletes `~/.owlbear/copilot_token.json` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248-249`.
- The helper patch set at `tests/test_content_guard_wiring_1321.py:108-138` does not patch `pathlib.Path.home()` or `Path.unlink()`, so these tests can mutate real operator state outside the workspace.
- A safe repo pattern already exists in `tests/test_server_1317.py:247-309`, which patches `pathlib.Path.home` to `tmp_path` before invoking `app_lifespan()`.

#### Test Integrity
- No visible weakening in the current `TestFromAC_*` file snapshot. I could not do a full before/after diff-based immutability check in this tool surface.

### Pass 2 — Informational
- `IngestPipeline.ingest()` still persists before guard scan at `serve/knowledge/src/owlbear_knowledge/ingest.py:275-294`, but the task body marks that path out of scope for 1321 and assigns the ordering fix to #1322, so I did not gate this review on it.

### Deductions
- `-0.13` Task-local lifespan tests can delete a real home-directory token file unless sandboxed.
- `-0.03` Direct git diff / dirty-tree contamination checks were unavailable, so integrity assessment is based on current file state plus task history.

### Verdict
- Confidence: 0.84
- FAIL
- Route: `todo` — implementation and refined AC behavior are present; only test-file safety fixes remain. I did not apply automatic backlog loop-breaker routing because the intervening architecture refinement materially reset the prior AC2 dispute, and the current failure is a new test-safety defect.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Sandbox the AC1 `app_lifespan()` tests by patching `pathlib.Path.home()` to `tmp_path` (or otherwise isolating the token path) so the suite cannot touch `~/.owlbear/copilot_token.json` on the reviewer/builder machine | `tests/test_content_guard_wiring_1321.py` | `tests/test_content_guard_wiring_1321.py:153`, `:168`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248-249`; safe pattern in `tests/test_server_1317.py:247-309` |
| 2 | test-writer | Add an explicit regression assertion that the lifespan-wiring tests exercise only the sandboxed home path, following the existing `test_server_1317.py` pattern, before returning to review | `tests/test_content_guard_wiring_1321.py` | `tests/test_content_guard_wiring_1321.py:108-138` currently patches heavy services but not `Path.home`/`Path.unlink` |

### Post-task Reflection
- The first parallel quality-runner lint report contained a stale file/line claim; a targeted scoped rerun prevented a false lint failure.
- The binding contract for this task lived in a later Architecture Review section, not just the top-level AC list.
- Existing safe-path evidence in `tests/test_server_1317.py` made the required follow-up concrete instead of speculative.
[[2026-05-04]]
## Test-Writer Notes
- Retry: sandboxed `TestFromAC_LifespanGuardWiring` lifespan tests per reviewer Required Follow-up #1 and #2.
- **All 32 tests pass** against current implementation — test-only retry, builder skip.

### Changes made to `tests/test_content_guard_wiring_1321.py`

1. Added `from pathlib import Path` import.
2. Added class-level `autouse` fixture `_sandbox_lifespan_home` to `TestFromAC_LifespanGuardWiring` — patches `pathlib.Path.home` to `tmp_path` via `monkeypatch.setattr`, isolating all 5 prior lifespan tests from real `~/.owlbear/copilot_token.json`.
3. Added new test `test_lifespan_token_cleanup_operates_in_sandboxed_home` — explicit regression assertion (Follow-up #2): creates a token file in `tmp_path/.owlbear/copilot_token.json`, runs `app_lifespan`, asserts file is deleted, confirming `Path.home()` is redirected and the real home is never touched.

### Test summary

| Class | Tests | Status |
|---|---|---|
| `TestFromAC_LifespanGuardWiring` | 6 (was 5) | all pass ✓ |
| `TestFromAC_BlockAndWarnBehavior` | 8 | all pass ✓ |
| `TestFromAC_ScanOrdering` | 3 | all pass ✓ |
| `TestFromAC_SearchPathNoGuard` | 3 | all pass ✓ |
| `TestFromAC_AllSourceTypesScanned` | 11 | all pass ✓ |
| `_contextlib_exitstack` | 1 | all pass ✓ |
| **Total** | **32** | **all pass ✓** |

### Lint
- `ruff check tests/test_content_guard_wiring_1321.py` — clean ✓

### Rationale for direct-to-review advance
All 32 tests pass against the existing implementation. The implementation already handles guard wiring correctly; only the test safety gap (real home deletion risk) needed patching. Builder has no work to do.
[[2026-05-04]]
## Builder Notes
- No code changes in this builder cycle.
- This is a test-only pass-through after test-writer safety retry; implementation already satisfied the refined AC.
- Verification (scoped):
  - `uv run pytest tests/test_content_guard_wiring_1321.py --cov=owlbear_knowledge.ingest --cov=owlbear_mcp_knowledge.server --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
  - `uv run ruff check serve/knowledge/src/owlbear_knowledge/ingest.py serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_content_guard_wiring_1321.py`
- Results:
  - Tests: 32 passed, 0 failed, 0 skipped
  - Coverage: `owlbear_knowledge.ingest` 52%, `owlbear_mcp_knowledge.server` 44%, overall 31%
  - Lint: clean (0 issues)
- Evidence summary:
  - AC1/AC2/AC3/AC4/AC5 remain satisfied by the existing implementation and the updated `TestFromAC_*` suite.
  - Reviewer safety concern was addressed by test-writer sandboxing in `tests/test_content_guard_wiring_1321.py`; builder had no further implementation action.
- Fixes applied:
  - None in this cycle (pass-through validation only).
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped: 32 passed, 0 failed, 0 skipped for `tests/test_content_guard_wiring_1321.py`
- Runtime: 2.53s

### Lint Results
- `ruff check` clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`

### Coverage
- `owlbear_knowledge.ingest`: 52%
- `owlbear_mcp_knowledge.server`: 44%
- overall scoped run: 31%
- Informational only: the gate here is AC proof on the task-owned guarded path, not module-wide percentages.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — guard instantiated in `app_lifespan`, passed to `IngestPipeline`, and `scan()` runs during `ingest_text()` | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:288-289` instantiates `ContentInjectionGuard()` and constructs `IngestPipeline(..., content_guard=content_guard)`; `serve/knowledge/src/owlbear_knowledge/ingest.py:106-116` scans each chunk before persistence | `test_app_lifespan_passes_content_guard_to_ingest_pipeline`, `test_content_guard_is_content_injection_guard_instance`, `test_ingest_text_calls_scan_on_guard`, `test_ingest_text_scans_every_chunk`, plus sandbox regression `test_lifespan_token_cleanup_operates_in_sandboxed_home` | PASS |
| AC2 — strict blocks/not stored; non-strict warns and persists | I anchored to the latest binding Architecture Review refinement at `.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md:321` and the proof table at `:330-334`, not the stale top-level checklist wording at `:27`. The parent brief also frames the boundary as content reaching storage "as chunks" at `.owlbear/briefs/draft-knowledge-activation/brief.md:113`. Live behavior exists at `serve/knowledge/src/owlbear_knowledge/ingest.py:107-116`. | Strict: `test_strict_mode_blocked_content_not_stored` (`tests/test_content_guard_wiring_1321.py:292` / `:303`) and `test_strict_mode_blocked_result_has_zero_entity_and_edge_counts` (`:307-319`). Non-strict: `test_non_strict_mode_logs_warning_on_threat` (`:339`), `test_non_strict_mode_returns_ok_status_on_threat` (`:366`), `test_non_strict_threat_content_reaches_store_chunks` (`:383-425`) | PASS |
| AC3 — `scan()` completes before `store_chunks()` | `serve/knowledge/src/owlbear_knowledge/ingest.py:106-116` scans before any `ingest_text()` persistence calls at `:160-166` | `test_scan_called_before_store_chunks` (`tests/test_content_guard_wiring_1321.py:451-481`), `test_blocked_scan_prevents_store_chunks` (`:485-517`), `test_multi_chunk_blocked_first_stops_before_second` (`:521-552`) | PASS |
| AC4 — search/query path does not invoke guard on pre-existing chunks | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:375` calls `qs.query(...)` directly; no guard hook is present on the query path | `test_search_knowledge_does_not_invoke_guard_scan` (`tests/test_content_guard_wiring_1321.py:568-585`), `test_query_service_called_without_guard_in_call_chain` (`:588-601`) | PASS |
| AC5 — all `source_type` values passed to `ingest_text()` are scanned | `serve/knowledge/src/owlbear_knowledge/ingest.py:106` scans every chunk whenever a guard exists; no `source_type` exemption exists in `ingest_text()` | `test_guard_scans_for_source_type` (`tests/test_content_guard_wiring_1321.py:654-671`), `test_trusted_source_types_are_not_exempt_in_ingest_text` (`:675-694`), `test_absent_metadata_still_triggers_scan` (`:698-708`) | PASS |

### Pass 1 — Critical Checks
#### Test-Writer AC Coverage
- PASS. The live `TestFromAC_*` suite now proves every refined AC line. I diverged from code-reader's strict-side `insert_document` concern because the latest Architecture Review explicitly treats `test_strict_mode_blocked_content_not_stored` as the AC2 proof for "blocked, not stored" and the parent brief defines the storage boundary as chunks, not every internal persistence call.

#### Security / Data Safety
- PASS for the in-scope `app_lifespan`, `ingest_text()`, and `search_knowledge()` paths.
- Informational only: the sibling `ingest()` path still persists before scan at `serve/knowledge/src/owlbear_knowledge/ingest.py:275-291`, but the task body marks `ingest()` out of scope and assigns that implementation concern to #1322.

#### Test Integrity
- PASS with reduced confidence. The current snapshot retains all `TestFromAC_*` classes with no visible weakening, and the builder commit `cd74db6e2cd965b5b9c226e77336c829545a66f8` is present in `.git/logs/refs/heads/dev:1639` and `.git/logs/HEAD:1789`.
- Full diff-based immutability and dirty-tree contamination checks were not available in this tool surface, so integrity is not maximum-confidence.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC-mapped assertions pin guard wiring, blocked status, no chunk storage in strict mode, warning log in non-strict mode, exact non-strict `status == "ok"`, non-strict persistence via `store_chunks()`, query-path no-scan, and source-type coverage |
| Negative / error-path coverage | STRONG | Strict block, no-guard passthrough, blocked short-circuit, multi-chunk stop, and non-strict threat behavior are all exercised |
| Manual mutation reasoning | ADEQUATE | Reversing scan/store order, dropping the warning, blocking non-strict content, or exempting source types would fail. A mutation that moved `insert_document` earlier would not, but that exceeds the task-owned chunk-storage contract as refined in the Architecture Review |
| Test independence | STRONG | Fresh mocks, pipelines, and call logs per test |
| Naming | STRONG | Test names map directly to the AC language |

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 4 |
| Assessment | CLEAN — later builder sections are pass-through verification only; no retry loop defect in the implementation work |

### Pass 2 — Informational
- Canonical contract drift remains in the task artifact: the stale top-level AC2 text at `.owlbear/kanban/tasks/1321-p0-05-tests-content-injection-guard-wiring-at-ingest.md:27` coexists with the later refined AC2 at `:321`. I anchored this review to the latest Architecture Review and its explicit REFINE-then-APPROVE verdict at `:368` / `:375`.
- The sandbox fix is now present and effective: `tests/test_content_guard_wiring_1321.py:150` redirects `Path.home()`, and `:220-241` proves token cleanup operates only inside the sandboxed tmp path.

### Deductions
- `-0.03` Full git diff / dirty-tree overlap checks were unavailable in this tool surface.
- `-0.02` The task artifact still contains stale top-level AC2 wording alongside the later refined binding AC, which adds a small interpretation risk.

### Verdict
- Confidence: 0.93
- PASS
- Route: `docs`

### Post-task Reflection
- The binding contract for this review lived in a late Architecture Review refinement, not the original checklist header.
- The parent brief resolved the biggest proof-quality dispute by framing the storage boundary as chunk storage.
- `.git/logs/**` was enough to confirm builder commit presence when full diff access was unavailable, but not enough to remove all integrity doubt.
[[2026-05-04]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/knowledge/README.md` lists `IngestPipeline` under Ingestion — no guard behavior claims, no stale assertions. `serve/mcp-knowledge/README.md` describes tools at the API level; guard is an implementation detail not exposed there. No prose doc updates needed. |
| 2 | Module docstrings | Yes | Updated | `IngestPipeline` class docstring (L56-60) said "untrusted-source chunk text is scanned" — inaccurate: AC5 confirmed unconditional scan with no `source_type` exemption. Fixed to "every chunk's text is scanned … no `source_type` value is exempt." `app_lifespan` and `ingest_text` docstrings accurate. |
| 3 | External attribution | No | N/A | No external repos or articles cited. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/content-guard-wiring-tests.md` exists; linked in task body under Research section. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` has `describes: serve/mcp-*/src/**, serve/knowledge/src/**` — matches both changed files. Footer updated from `(3b857809)` to `(b844bdcf)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/knowledge/src/owlbear_knowledge/ingest.py` | IN | Docstring fixed (Item 2) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN | Docstring verified accurate |
| `tests/test_content_guard_wiring_1321.py` | OUT | Test file — no docstring obligation |

### Files Updated
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — `IngestPipeline.content_guard` docstring
- `share/diagrams/mcp-topology.excalidraw` — footer hash

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1321-*` files found)

Commit: `de2018bf` — docs: fix IngestPipeline docstring and update mcp-topology diagram (#1321, doc-writer)
[[2026-05-04]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — Guard instantiated in app_lifespan, passed to IngestPipeline, scan() called in ingest_text() | Commit cd74db6e wires guard in server.py:288-293 and ingest.py:106-116; 6 tests cover this in test_content_guard_wiring_1321.py | PASS |
| AC2 — Strict blocks/not stored; non-strict warns and persists (refined) | Binding contract is Architecture Review loop-breaker at task body; tests at L292, L335, L366, L383 prove strict block + non-strict warn+persist | PASS |
| AC3 — scan() before store_chunks() ordering | Call-order assertions at L451, L485, L521 would fail on reversed ordering | PASS |
| AC4 — Search/query path does not invoke guard (D20) | Query path at server.py:375 calls qs.query() directly; regression guards at L568, L588 | PASS |
| AC5 — All source_type values scanned, no exemption | Unconditional scan at ingest.py:106; parametrized tests at L654, L675, L698 | PASS |

### Test Results
- pytest (task-scoped): 32 passed, 0 failed
- pytest (full suite): 4056 passed, 244 failed — no failures in task scope
- vitest (full suite): 948 passed, 15 failed — no failures in task scope
- ruff: 1 T201 violation (not in task files)
- eslint: 1 react-hooks error (not in task files)

### Commit Integrity
- cd74db6e — feat: wire ingest guard at lifespan/text path (#1321, builder) — 2 source files
- 3577dec9 — test: strengthen AC2 non-strict persistence proof (#1321, test-writer) — test file
- de2018bf — docs: fix IngestPipeline docstring and update mcp-topology diagram (#1321, doc-writer) — docstring + diagram

All properly scoped. No unrelated files in commits.

### Architect Quality: 3/5
Original AC2 conflated behavior (block/warn) with ordering (scan-before-store), causing 2 unnecessary review cycles before loop-breaker refinement resolved the ambiguity. AC3 already owned ordering, making the "before chunk storage" modifier in AC2 a source of interpretation dispute.

### Deduction Breakdown
- -.03 AC quality score ≤ 3 (ordering ambiguity in AC2 caused 2 unnecessary review cycles)
- -.01 Full git diff/dirty-tree checks unavailable in tool surface (reviewer also noted this)

### Confidence: .96
### Action: archive