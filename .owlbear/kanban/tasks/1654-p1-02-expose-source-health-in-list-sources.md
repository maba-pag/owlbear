---
id: 1654
title: 'P1-02: Expose source health in list_sources'
status: review
priority: needed
created: 2026-05-18T03:11:18.823946+02:00
updated: 2026-05-18T16:03:44.731063+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on:
  - 1651
ac:
  - 'AC-1: `SourceInfo` TypedDict includes keys `last_refreshed_at: str | None`, `last_checked_at:
    str | None`, `last_error: str | None`, `enabled: bool`, `fetch_method: str`.'
  - 'AC-2: `list_sources` response dict maps `last_refreshed_at`, `last_checked_at`,
    `enabled`, and `fetch_method` directly from `KnowledgeSource` attributes. `last_error`
    is mapped through `_sanitize_error()` (AC-3/AC-4) before inclusion.'
  - 'AC-3: Module-private `_sanitize_error(raw: str | None) -> str | None` in `server.py`:
    returns `None` when input is `None`; otherwise searches raw text for the first
    match of pattern `[A-Z][a-zA-Z]*(Error|Exception)` (with a negative lookbehind
    rejecting matches whose first uppercase letter is immediately preceded by `/`
    or `\`) or `HTTP \d{3}`. If no valid match exists, returns the fixed string `"error"`.
    Output never exceeds 120 characters.'
  - "AC-4: `_sanitize_error` input/output pairs: `\"PermissionError: [Errno 13] ...'/home/user/secret.pem'\"\
    ` -> `\"PermissionError\"`; `\"HTTP 503 Service Unavailable from internal.corp:8080\"\
    ` -> `\"HTTP 503\"`; `\"no files matched source path '/secret/data'\"` -> `\"\
    error\"`; `\"ConnectionError: refused; TimeoutError: timed out\"` -> `\"ConnectionError\"\
    `; `\"no files matched source path '/secret/TimeoutError'\"` -> `\"error\"` (path-preceded
    token rejected by lookbehind)."
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-18T16:03:44.731063+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Expand `SourceInfo` TypedDict and `list_sources` MCP tool response with 5 health fields.

**Out-of-scope:** `config` field (URL/endpoint leak risk per brief). `enrich` field (processing config, not health per brief D5). Refresh logic (O2). Source removal (O4).

## Context

Current `SourceInfo` has 4 keys: `id`, `name`, `source_type`, `scope`. Needs 5 additional keys from `KnowledgeSource`: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`.

`list_sources` currently builds response dicts with only the 4 existing keys. Must add the 5 new keys mapping from `KnowledgeSource` attributes.

Depends on #1651 because `last_checked_at` must exist in the model before it can be exposed.

[[2026-05-18T13:29:37+02:00]]
## Research

### Gate Checklist
1. **Validity** — Sound; standard field-exposure pattern
2. **Env audit** — No existing mechanism exposes health fields
3. **Prior art** — Same file maps 4 fields with identical TypedDict→dict pattern (L108–115, L1409–1415)
4. **Feasibility** — Zero blockers. Dep #1651 complete; all 5 target fields exist in `KnowledgeSource` model
5. **Arch fit** — MCP server owns TypedDict contract; no new imports or wiring
6. **Approach** — Add 5 fields to `SourceInfo` TypedDict, add 5 key-value pairs to dict comprehension. All primitives (`str | None`, `bool`, `str`) — direct attribute access
7. **Testing** — Extend `test_list_sources.py` (new keys + correct mapping) and `test_outputschema.py` (schema properties + types)

### Classification
T1 — Autonomous. Mechanical field expansion, established pattern, no decisions.

### No research doc
Trivial implementation with clear AC and no trade-offs. No follow-up tasks needed — ready for TDD.

[[2026-05-18T13:53:20+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expose health fields in list_sources response |
| Interface clarity | PASS | AC specifies exact field names, types, and mapping source |
| Dependency correctness | PASS | #1651 archived — last_checked_at field exists in model |
| Module layering | PASS | MCP server reads from knowledge model (correct direction) |
| TDD compliance | PASS | Standard pipeline; test-writer processes at todo |
| KISS/YAGNI | PASS | Minimal scope — 5 key-value pairs added to existing pattern |
| Premise challenge | PASS | Health exposure required for Cockpit source monitoring |
| Pattern consistency | PASS | Same TypedDict→dict pattern as existing 4 fields (L108–116, L1409–1422) |
| Security surface | PASS | config field deliberately excluded (leak risk per brief); only metadata exposed |
| Single domain | PASS | scope:mcp-knowledge only; consolidation-test #1655 covers cross-domain family |

### Challenge Results
- Challenger: reconsider (0.74)
- Findings: (1) interface characterization — correctly identifies this as public MCP contract growth, not zero-interface work; (2) existing tests don't cover new fields — expected, TDD pipeline handles this; (3) AC-1 is shape declaration — still mechanically testable by test-writer
- Architect response: Override to APPROVE. Accept framing correction (interface growth acknowledged). No AC refinement needed — exact field names/types are sufficient for test derivation. No consolidation-test gap (existing #1655). No architectural defect found.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Advanced to todo. Behavioral TDD — test-writer will derive TypedDict shape tests and response mapping assertions from AC.

[[2026-05-18T14:08:38+02:00]]
## Test-Writer Notes
- Test file: tests/test_list_sources_1654.py
- Classes: TestFromAC_SourceInfoShape, TestFromAC_SourceInfoOutputSchema, TestFromAC_ListSourcesHealthMapping
- Tests per category: happy 13, edge 4, error 0, boundary 3
- Total: 30 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests | Class |
|----|-------|-------|
| AC-1 TypedDict shape (presence + type) | 10 | TestFromAC_SourceInfoShape |
| AC-1 output schema (5 new fields) | 7 | TestFromAC_SourceInfoOutputSchema |
| AC-2 response mapping (per-field + None/False/empty/multi) | 13 | TestFromAC_ListSourcesHealthMapping |

[[2026-05-18T14:20:17+02:00]]
## Builder Notes
- Implementation: Added 5 health fields to SourceInfo and list_sources response mapping in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Approach: Surgical TypedDict + response-shape expansion only; no API flow changes or additional logic.
- RED verification (quality-runner): tests/test_list_sources_1654.py -> 30 failed before implementation (all TestFromAC_* classes)
- GREEN verification (quality-runner): tests/test_list_sources_1654.py -> 30 passed, 0 failed
- Lint (quality-runner): clean for serve/mcp-knowledge/src/ and tests/test_list_sources_1654.py
- Coverage (quality-runner scoped): module owlbear_mcp_knowledge.server at 28% in scoped run (task tests target a narrow list_sources/SourceInfo contract in a large module)
- Durable module baseline check pre-change: serve/mcp-knowledge/tests/test_list_sources.py -> 17 passed, 1 failed
- Durable module check post-change: serve/mcp-knowledge/tests/test_list_sources.py -> 17 passed, 1 failed (same existing failure: TestFromAC_ListSources::test_calls_list_all_via_asyncio_to_thread)
- Commit: f06a3339 feat: expose source health in list_sources (#1654, builder)
- Evidence summary: AC-1 satisfied by SourceInfo keys/types and schema reflection; AC-2 satisfied by direct field mapping from KnowledgeSource attributes for each returned source.

[[2026-05-18T14:40:11+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL summary: FAIL #1654 -> backlog | exposing raw last_error leaks persisted exception/path details through list_sources.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1, AC-2 | The new public list_sources contract exposes raw last_error text, but last_error is persisted from unsanitized exception/path strings and then returned verbatim on the MCP read surface. That is an information-disclosure regression on a documented tool surface, and the task tests codify raw passthrough instead of safe disclosure. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:117,1421; serve/knowledge/src/owlbear_knowledge/refresh.py:241,287,315,387,463,465; .owlbear/briefs/draft-knowledge-source-lifecycle/stances/security.md:9,13,15; tests/test_list_sources_1654.py:284,415; serve/mcp-knowledge/README.md:22 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the source-health exposure contract so last_error is sanitized before any MCP read surface and update the AC/scope to reflect the safe-disclosure rule. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py; serve/knowledge/src/owlbear_knowledge/refresh.py; .owlbear/briefs/draft-knowledge-source-lifecycle/stances/security.md; tests/test_list_sources_1654.py | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1421; serve/knowledge/src/owlbear_knowledge/refresh.py:241,287,315,387,463,465; .owlbear/briefs/draft-knowledge-source-lifecycle/stances/security.md:9,13,15 |
| 2 | test-writer | Replace raw last_error passthrough assertions with safe-disclosure coverage after the architect refines the contract. | tests/test_list_sources_1654.py | tests/test_list_sources_1654.py:284,415 |

## Observations
- Builder evidence was otherwise internally consistent: scoped task-test pass/lint evidence matched the current file state, and editor diagnostics reported no errors in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py or tests/test_list_sources_1654.py.
- The mechanical field additions themselves are narrow and correctly wired; the rejection is specifically about the public-contract/security implications of exposing unsanitized last_error.

[[2026-05-18T14:52:44+02:00]]
## Architecture Review (Re-review after Reviewer Rejection)
### Context
Reviewer rejected with FAIL: raw `last_error` passthrough leaks persisted exception/path details through the public `list_sources` MCP surface. Reviewer directed architect to refine contract with safe-disclosure rule.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expose health fields with sanitization in list_sources |
| Interface clarity | PASS | AC-3/AC-4 specify exact extraction rules and input→output pairs |
| Dependency correctness | PASS | #1651 archived — last_checked_at field exists in model |
| Module layering | PASS | MCP server reads from knowledge model (correct direction); sanitization at trust boundary |
| TDD compliance | PASS | Task tests must be rewritten for sanitized contract — test-writer will derive from AC-3/AC-4 |
| KISS/YAGNI | PASS | Minimal regex extraction, no over-engineering |
| Premise challenge | PASS | Security stance in brief confirms need; reviewer empirically demonstrated the disclosure risk |
| Pattern consistency | PASS | Browser-fetcher comment at server.py:63-65 shows codebase awareness of error-text leakage |
| Security surface | PASS | AC-3 explicitly prevents path/hostname/URL disclosure; fixed fallback prevents unknown leaks |
| Single domain | PASS | scope:mcp-knowledge only; sanitization stays at MCP server layer (trust boundary) |

### Design Decision: Read-time vs Write-time Sanitization
The brief's security stance recommends write-time sanitization in `_update_source_record` (knowledge package). However:
- Write-time is in `knowledge` domain (different package, different task scope)
- The MCP server IS the trust boundary — it should sanitize regardless of storage format
- `refresh_source` also returns raw errors (separate surface, separate fix)
- Read-time sanitization in mcp-knowledge is architecturally correct for THIS task

Broader write-time sanitization and `refresh_source` parity are follow-up concerns outside this task's domain.

### Parent Constraint Override
Parent #1650 Key Constraints says \"Raw error strings (no sanitization)\" — this is contradicted by the brief's own security panel (stances/security.md) which explicitly recommends sanitization. The reviewer's rejection validates the security panel's position. The parent constraint is overridden.

### Challenge Results
- Challenger: reconsider (0.54)
- Findings: (1) read-time narrower than brief's write-time recommendation — accepted as scoping decision, not defect; (2) AC-3 extraction rules needed tightening — addressed by adding deterministic regex patterns and fixed fallback in refined AC; (3) refresh_source cross-surface inconsistency — acknowledged as separate follow-up; (4) existing-field retention implicit — covered by existing durable tests
- Architect response: Override to APPROVE. Refined AC-3/AC-4 with deterministic regex extraction rules. Scoping decision (read-time at trust boundary) is architecturally sound. Broader sanitization is separate work.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (existing task tests must be rewritten for sanitized contract)

### Scope Note for Test-Writer
The existing tests/test_list_sources_1654.py asserts raw passthrough (e.g., `== "Connection refused"`). These assertions must be replaced with sanitized-output assertions matching AC-3/AC-4. The test-writer should delete/rewrite the task test file.

### Verdict: APPROVE
### Action Taken: Refined AC with sanitization contract (AC-3/AC-4). Advanced to todo. Behavioral TDD — test-writer will derive sanitizer tests and update response mapping assertions.

[[2026-05-18T15:01:53+02:00]]
## Test-Writer Notes
- Test file: tests/test_list_sources_1654.py
- Classes: TestFromAC_SourceInfoShape, TestFromAC_SourceInfoOutputSchema, TestFromAC_SanitizeError, TestFromAC_ListSourcesHealthMapping
- Tests per category: happy 17, edge 6, error 4, boundary 4 (AC-4 canonical pairs)
- Total: 46 tests, all FAIL (ImportError: cannot import name '_sanitize_error' from owlbear_mcp_knowledge.server)
- ruff: clean

### Retry changes
- Full rewrite per architect instruction (raw passthrough tests codified rejected security behavior)
- Added TestFromAC_SanitizeError (13 tests): AC-3 None→None, error class extraction, exception suffix, HTTP status, first-match wins, 120-char limit, fallback "error", empty string; AC-4 all 4 canonical input/output pairs
- Updated TestFromAC_ListSourcesHealthMapping: replaced 2 raw last_error passthrough tests with 5 sanitized-contract tests (error class, HTTP status, no-match→"error", no-path-leak, full-field assertions using sanitizable input)
- Kept AC-1 shape (10) and schema (7) tests unchanged

### AC Coverage
| AC | Tests | Class |
|----|-------|-------|
| AC-1 TypedDict shape (presence + type) | 10 | TestFromAC_SourceInfoShape |
| AC-1 output schema (5 new fields) | 7 | TestFromAC_SourceInfoOutputSchema |
| AC-3/AC-4 _sanitize_error contract | 13 | TestFromAC_SanitizeError |
| AC-2 response mapping (last_error sanitized + other 4 direct) | 16 | TestFromAC_ListSourcesHealthMapping |

[[2026-05-18T15:09:38+02:00]]
## Builder Notes
- Implementation: Added module-private sanitizer `_sanitize_error(raw: str | None) -> str | None` and routed `list_sources` `last_error` through sanitizer in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`.
- Files changed: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- Approach: Surgical trust-boundary sanitization only. Regex extracts first safe token (`[A-Z][a-zA-Z]*(Error|Exception)` or `HTTP \d{3}`), falls back to fixed `"error"`, preserves `None`, and defensively collapses non-string values to `"error"`.
- RED verification (quality-runner): `tests/test_list_sources_1654.py` failed at collection pre-implementation (`ImportError: cannot import name '_sanitize_error'`).
- GREEN verification (quality-runner): `tests/test_list_sources_1654.py` -> 46 passed, 0 failed.
- Lint (quality-runner): clean for `serve/mcp-knowledge/src/` and `tests/test_list_sources_1654.py`.
- Coverage (quality-runner scoped): `owlbear_mcp_knowledge.server` 29% in scoped run.
- Durable module baseline pre-change: `serve/mcp-knowledge/tests/test_list_sources.py` -> 17 passed, 1 failed (`test_calls_list_all_via_asyncio_to_thread`).
- Durable module check post-change: `serve/mcp-knowledge/tests/test_list_sources.py` -> 17 passed, 1 failed (same existing failure; no regression from task change).
- Commit: `a259b6d4b318cddb584618b0b2f6d232aa46574d` `feat: sanitize list_sources last_error exposure (#1654, builder)`.
- Evidence summary: AC-1/AC-2 interface remains intact for all five health fields; AC-3/AC-4 sanitizer contract is implemented and verified by task-scoped tests.

[[2026-05-18T15:21:16+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL summary: FAIL #1654 -> backlog | _sanitize_error can still expose Error/Exception tokens derived from source-path text, so the disclosure class is not actually closed.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-3, AC-4 | The sanitizer searches the entire persisted error string and returns the first `Error`/`Exception` token it sees, even when that token comes from configured source-path text rather than an exception label. `refresh.py` persists raw `source.config['path']` text into `last_error`, so a path like `/secret/TimeoutError` would be exposed through `list_sources` as `TimeoutError`. The current AC/examples and task tests only prove the non-matching path case, so the retry still false-greens the original disclosure concern. | serve/knowledge/src/owlbear_knowledge/refresh.py:287,465; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:210,213,219,222,1438; tests/test_list_sources_1654.py:282,491,503 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the sanitizer contract so list_sources never returns `Error`/`Exception` tokens sourced from configured path text, and add an explicit AC example for a path basename such as `/secret/TimeoutError` that must sanitize to the fixed fallback instead of echoing the basename token. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py; serve/knowledge/src/owlbear_knowledge/refresh.py; tests/test_list_sources_1654.py | serve/knowledge/src/owlbear_knowledge/refresh.py:287,465; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:210,213,219,222,1438; tests/test_list_sources_1654.py:282,491,503 |
| 2 | architect | Tighten the proof expectations for the retry so task-local tests must include the path-token leakage case rather than only the non-matching path fallback case. | tests/test_list_sources_1654.py | tests/test_list_sources_1654.py:282,491,503 |

## Observations
- Builder evidence was otherwise internally consistent: the claimed task-local pass/lint state matches the current file state, and editor diagnostics are clean in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_list_sources_1654.py`.
- The adjacent durable failure in `serve/mcp-knowledge/tests/test_list_sources.py` around `asyncio.to_thread` remains unchanged from the builder's pre/post baseline and is not the reason for this rejection.
- The current 120-character cap test is weak because it uses a short matched token (`ValueError`) and would still pass without the slice; that is a non-blocking proof-quality note, not the route-driving defect.

[[2026-05-18T15:33:05+02:00]]
## Architecture Review (Third cycle — path-token disclosure fix)
### Context
Second reviewer rejection: `_sanitize_error` regex `.search()` matches Error/Exception tokens from path text embedded in `last_error`. Example: `/secret/TimeoutError` → sanitizer returns `TimeoutError` instead of fallback `"error"`. Reviewer directed: add explicit AC example for path-basename leakage and tighten proof expectations.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expose health fields with path-safe sanitization |
| Interface clarity | PASS | AC-3 specifies exact regex with lookbehind; AC-4 has 5 deterministic I/O pairs |
| Dependency correctness | PASS | #1651 archived — all model fields exist |
| Module layering | PASS | MCP server reads from knowledge model; sanitization at trust boundary |
| TDD compliance | PASS | Task tests must be rewritten for path-safe contract |
| KISS/YAGNI | PASS | Single negative lookbehind addition to existing regex — minimal fix |
| Premise challenge | PASS | Reviewer empirically demonstrated the disclosure path |
| Pattern consistency | PASS | Same regex-based sanitizer pattern, refined constraint |
| Security surface | PASS | AC-4 pair 5 explicitly proves path-token rejection; AC-3 prevents `/` and `\\` preceded tokens |
| Single domain | PASS | scope:mcp-knowledge only |

### Design Decision: Lookbehind scope
Narrowed path separators to `/` and `\\` only (dropped `.`). Rationale: dotted module references (e.g., `requests.exceptions.ConnectionError` in a stringified error) are legitimate Error tokens we WANT to extract. No evidence of dotted-path disclosure in `last_error` persistence paths (refresh.py uses `str(exc)` and f-strings with file paths, not module paths).

### Challenge Results
- Challenger: reconsider (0.44)
- Findings: (1) lookbehind position concern — challenger misread regex semantics; lookbehind checks char before first `[A-Z]` of token, correctly rejects `/TimeoutError`; (2) canonical artifact mismatch — expected, edit_task updates AC; (3) AC-1/AC-2 B2 weakness — non-blocking, two prior test-derivation cycles proved adequacy; (4) dot separator scope — valid, dropped `.` per challenger's evidence gap
- Architect response: Override to APPROVE. Lookbehind proof is sound. Path-separator set narrowed per valid challenger feedback. AC-4 pair 5 closes the specific gap reviewer identified.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (task tests must be rewritten for path-safe contract per AC-3/AC-4 refinement)

### Scope Note for Test-Writer
The existing tests/test_list_sources_1654.py must gain coverage for AC-4 pair 5 (`/secret/TimeoutError` → `"error"`). The `_sanitize_error` regex needs `(?<![/\\\\])` negative lookbehind before the `[A-Z]` token start. Rewrite sanitizer tests accordingly.

### Verdict: APPROVE
### Action Taken: Refined AC-3/AC-4 with negative-lookbehind path-separator guard. Added canonical pair 5 for path-token rejection. Advanced to todo.

[[2026-05-18T15:43:00+02:00]]
## Test-Writer Notes
- Test file: tests/test_list_sources_1654.py
- Classes: TestFromAC_SourceInfoShape, TestFromAC_SourceInfoOutputSchema, TestFromAC_SanitizeError, TestFromAC_ListSourcesHealthMapping
- Tests per category: happy 17, edge 8, error 4, boundary 6 (incl. AC-4 pairs 1–5)
- Total: 49 tests (46 pre-existing pass, 3 new fail)
- ruff: clean

### Retry changes (3rd cycle — path-token lookbehind gap)
- Added `TestFromAC_SanitizeError::test_ac4_path_preceded_error_token_returns_fallback`: AC-4 pair 5 — `"no files matched source path '/secret/TimeoutError'"` → `"error"` (path-preceded token rejected by lookbehind)
- Added `TestFromAC_SanitizeError::test_backslash_preceded_error_token_returns_fallback`: AC-3 backslash separator guard — backslash-preceded Error token returns `"error"`
- Added `TestFromAC_ListSourcesHealthMapping::test_response_last_error_path_preceded_token_sanitized_to_fallback`: end-to-end mapping assertion that path-token in `last_error` produces `"error"` in response

### AC Coverage
| AC | Tests | Class |
|----|-------|-------|
| AC-1 TypedDict shape (presence + type) | 10 | TestFromAC_SourceInfoShape |
| AC-1 output schema (5 new fields) | 7 | TestFromAC_SourceInfoOutputSchema |
| AC-3/AC-4 _sanitize_error contract (incl. pair 5) | 15 | TestFromAC_SanitizeError |
| AC-2 response mapping (last_error sanitized + other 4 direct) | 17 | TestFromAC_ListSourcesHealthMapping |

### RED verification
- quality-runner: 3 failed, 46 passed (new tests fail; existing tests pass)
- Commit: b460ec87

[[2026-05-18T16:02:54+02:00]]
## Builder Notes
- Implementation: Updated sanitizer token regex in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py) to reject Error/Exception matches when the token is path-preceded by `/` or `\\`.
- Files changed: [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py).
- Approach: Surgical one-line regex refinement to satisfy AC-3/AC-4 path-token guard while preserving existing Error/Exception and HTTP status extraction behavior.
- RED verification (quality-runner): [tests/test_list_sources_1654.py](tests/test_list_sources_1654.py) -> 46 passed, 3 failed before implementation.
- GREEN verification (quality-runner): [tests/test_list_sources_1654.py](tests/test_list_sources_1654.py) -> 49 passed, 0 failed.
- Lint (quality-runner): clean for [serve/mcp-knowledge/src/](serve/mcp-knowledge/src/) and [tests/test_list_sources_1654.py](tests/test_list_sources_1654.py).
- Coverage (quality-runner scoped): module owlbear_mcp_knowledge.server at 29% in scoped run (task tests cover a narrow contract inside a large module).
- Durable module baseline pre-change: [serve/mcp-knowledge/tests/test_list_sources.py](serve/mcp-knowledge/tests/test_list_sources.py) -> 17 passed, 1 failed (existing failure: TestFromAC_ListSources::test_calls_list_all_via_asyncio_to_thread).
- Durable module post-change: [serve/mcp-knowledge/tests/test_list_sources.py](serve/mcp-knowledge/tests/test_list_sources.py) -> 17 passed, 1 failed (same existing failure; no regression introduced).
- Commit: 582663bb feat: reject path-preceded error tokens in sanitizer (#1654, builder).
- Evidence summary: New path-token guard now returns fallback "error" for slash/backslash-preceded error tokens, closing the three failing AC-3/AC-4 tests while keeping all prior task assertions green.
