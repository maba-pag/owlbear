---
id: 1890
title: 'Knowledge: MCP add register_source tool'
status: archived
priority: medium
created: 2026-05-27T01:00:59.214408+02:00
updated: 2026-05-27T11:00:38.207025+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - knowledge_register_source tool registered with readOnlyHint=False, 
    destructiveHint=False
  - Pydantic validation errors returned as MCP ToolError with detail
  - SourceRegistration constructed from tool params and passed to 
    SqliteSourceStore.register_source
  - Returns serialized SourceRecord (id, name, state, kind, scope)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Create new `knowledge_register_source` MCP tool. Accepts name, kind, fetch_method, config, scope, enrich, refreshable, priority, metadata. Validates typed SourceConfig discriminated union via Pydantic. Delegates to SqliteSourceStore.register_source(SourceRegistration).

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`

[[2026-05-27T03:05:55+02:00]]
## Research

Key findings:
- All downstream components ready: SqliteSourceStore.register_source(), SourceRegistration, SourceConfig discriminated union, AppContext.source_store_v2
- Critical design point: BoundaryModel uses strict=True; MCP JSON params need `model_validate(data, strict=False)` at boundary crossing
- Implementation: ~25 LOC new tool function + 1 TypedDict; follows existing tool pattern (get AppContext → validate → delegate → serialize)
- Return shape: {id, name, state, kind, scope} per AC
- No blockers; all dependencies satisfied

Doc: .owlbear/research/mcp-register-source-tool.md
Confidence: .88
No additional follow-up tasks needed — 1890 is the implementation unit.

[[2026-05-27T03:21:34+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One tool: register_source |
| Interface clarity | PASS | Inputs (9 typed params), output (5-field TypedDict), error path (ToolError) all explicit |
| Dependency correctness | PASS | #1888 archived; source_store_v2 on AppContext confirmed |
| Module layering | PASS | MCP layer → store layer, no upward imports |
| TDD compliance | PASS | proof_bundle=behavioral, test-writer will write full TDD |
| KISS/YAGNI | PASS | ~25 LOC, one TypedDict, follows existing tool template exactly |
| Premise challenge | PASS | No existing tool covers source registration; genuine gap |
| Pattern consistency | PASS | Matches search_knowledge, list_sources patterns: decorator, Context, to_thread, ToolError |
| Security surface | PASS | Pydantic BoundaryModel validates all input; model_validate(strict=False) at MCP edge handles JSON coercion |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| model_validate | Invalid params | ValidationError | Yes → ToolError | Descriptive error message |
| source_store_v2 None | Store not initialized | ToolError | Yes (guard pattern) | Clear unavailability message |
| register_source | DB write error | sqlite3.Error | Propagates | Tool execution error |

### Design Diverge
- Skipped: single obvious approach (model_validate strict=False at boundary), no competing designs

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Architect response: proceeded with direct evaluation; AC lines are atomic, verifiable, and cover happy + error paths

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC clear and testable, architecture follows established patterns exactly.

[[2026-05-27T03:35:55+02:00]]
test-writer crashed once (no response); releasing claim before retry

[[2026-05-27T03:42:06+02:00]]
## Test-Writer Notes
- Test file: `tests/test_register_source_1890.py`
- Class: `TestFromAC_RegisterSourceTool`
- Total: 19 tests, all FAIL (ImportError: cannot import name 'knowledge_register_source' — function not yet implemented)
- Lint: ruff clean

### Tests by category
| Category | Count | Tests |
|----------|-------|-------|
| Happy path | 8 | delegation called once, SourceRegistration instance, name/kind/fetch_method/scope fields, default scope, non-default scope |
| Edge/boundary | 3 | scope defaults to global, source_store_v2 None → ToolError, exactly 5 return keys |
| Error path | 3 | invalid kind, invalid fetch_method, file_glob config missing patterns |
| Annotation/contract | 5 | tool importable, in mcp registry, readOnlyHint=False, destructiveHint=False, return fields (id/name/state/kind/scope) |

### AC coverage
| AC | Tests |
|----|-------|
| AC1 — registered with readOnlyHint=False, destructiveHint=False | test_tool_importable, test_tool_in_mcp_registry, test_readonlyhint_is_false, test_destructivehint_is_false |
| AC2 — Pydantic validation errors → ToolError | test_invalid_kind_raises_tool_error, test_invalid_fetch_method_raises_tool_error, test_file_glob_config_missing_patterns_raises_tool_error |
| AC3 — SourceRegistration constructed and delegated | test_delegates_to_source_store_v2_register_source, test_register_source_receives_source_registration_instance, test_registration_name_matches_input, test_registration_kind_coerced_from_string_enum, test_registration_fetch_method_coerced_from_string, test_scope_defaults_to_global, test_non_default_scope_passed_through, test_source_store_v2_none_raises_tool_error |
| AC4 — Returns serialized SourceRecord (id, name, state, kind, scope) | test_return_contains_id, test_return_contains_name, test_return_contains_state, test_return_contains_kind, test_return_contains_scope, test_return_has_exactly_five_keys |

[[2026-05-27T04:06:19+02:00]]
## Builder Notes
### Files Changed
- serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

### Implementation Summary
- Added new MCP tool `knowledge_register_source` with annotations `readOnlyHint=False`, `destructiveHint=False`.
- Added `RegisteredSourceResult` TypedDict return contract.
- Implemented boundary validation via `SourceRegistration.model_validate(..., strict=False)` to allow MCP JSON string coercion at boundary.
- Added validation error mapping: `ValidationError -> ToolError`.
- Added source-store availability guard: raises `ToolError` when `source_store_v2` is unavailable.
- Delegates registration to `SqliteSourceStore.register_source` via `asyncio.to_thread`.
- Returns serialized record with exactly: `id`, `name`, `state`, `kind`, `scope`.
- Exported `knowledge_register_source` in `__all__`.

### Verification Evidence
- RED verification (quality-runner, scoped):
  - test path: `tests/test_register_source_1890.py`
  - outcome: collection failed with ImportError (`knowledge_register_source` missing), confirming RED baseline.
- GREEN verification (quality-runner, scoped):
  - tests: 21 passed, 0 failed, 0 skipped
  - lint: clean (ruff clean)
  - coverage requested on `owlbear_mcp_knowledge.server`: 29% (module-wide legacy monolith; task-specific tests for new tool are all green)
- Module-level durable test file check:
  - `serve/mcp-knowledge/tests/test_*.py` not found; recorded as skip.

### Fixes Applied During GREEN
- Implemented tool function and result type.
- Adjusted import ordering for ruff.
- Made optional tool params keyword-only to satisfy boolean positional lint rules without changing behavior.

### Confidence
- 0.92

[[2026-05-27T04:29:27+02:00]]
## Review Evidence
- Verdict: FAIL
- Fail summary: FAIL #1890 to in-progress | invalid kind/config mismatch reaches the real store as ValueError and task proof misses it.

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2, AC3 | `knowledge_register_source` converts only `ValidationError` to `ToolError` before delegating. A mismatched `kind` and `config.kind` is still constructible at the protocol boundary and is rejected by the real store with `ValueError`, so invalid input can escape the MCP tool as a raw backend exception instead of a user-facing tool error. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:837-854; serve/knowledge/src/owlbear_knowledge/protocols/sources.py:112-118; serve/knowledge/src/owlbear_knowledge/stores/sources.py:79-82; tests/test_source_store_1870.py:175-184 | in-progress |
| 2 | AC2 | The task tests for error handling assert only the exception type. They never assert that the returned `ToolError` includes detail text, even though the implementation claims to surface `str(exc)`. A regression to a blank or generic message would still pass. | tests/test_register_source_1890.py:145-171; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:851-852 | in-progress |
| 3 | AC3 | Task proof uses a MagicMock store and only inspects `name`, `kind`, `fetch_method`, and `scope`. That does not prove the real store boundary behavior or the remaining registration params (`enrich`, `refreshable`, `priority`, `metadata`) that the tool forwards into `SourceRegistration`. | tests/test_register_source_1890.py:65-78; tests/test_register_source_1890.py:221-299 | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Normalize store-side invalid-input failures from `register_source` into `ToolError` so mismatched `kind` and `config.kind` and comparable real-store validation errors do not escape as raw `ValueError`. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | Blocking finding 1 |
| 2 | builder | Extend task proof to exercise the invalid-input boundary currently hidden by the mock store and assert the returned `ToolError` includes detail text. | tests/test_register_source_1890.py | Blocking findings 1 and 2 |
| 3 | builder | Add proof for the remaining registration params or narrow the implementation claim so the `SourceRegistration` contract is fully demonstrated. | tests/test_register_source_1890.py | Blocking finding 3 |

## Observations
- Builder evidence was otherwise internally consistent: AC1 registration metadata and AC4 return-shape serialization are directly supported by serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:816-860 and the targeted task tests.
- I did not independently rerun quality-runner because the builder packet was sufficient for evidence-first review and the blocking defects were established from direct code and test inspection.
- I could not independently perform the dirty-tree contamination check because git-status tooling is not available through this review environment.

[[2026-05-27T04:43:24+02:00]]
## Builder Notes
- RED check (quality-runner scoped): `tests/test_register_source_1890.py` -> 21 passed, 0 failed, ruff clean.
- Observation: current `TestFromAC_RegisterSourceTool` coverage does not exercise the reviewer-identified store boundary mismatch path (`kind` vs `config.kind`) at MCP tool level, and does not assert ToolError detail text.
- Builder constraint applied: per builder role rules, I did not modify tests and did not ship unproven source changes without a failing TestFromAC signal for this edge case.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add failing `TestFromAC_*` coverage for `knowledge_register_source` where payload `kind` and `config.kind` mismatch (e.g., `kind="inline"`, `config={"kind":"web"}`), and assert MCP-layer `ToolError` behavior. | tests/test_register_source_1890.py | Reviewer finding #1; builder RED check shows no current failing test for this boundary |
| 2 | test-writer | Strengthen AC2 proofs to assert ToolError detail content is present for invalid inputs, not only exception type. | tests/test_register_source_1890.py | Reviewer finding #2 |
| 3 | test-writer | Add assertions that `enrich`, `refreshable`, `priority`, and `metadata` are forwarded into `SourceRegistration` (or adjust AC/test intent explicitly). | tests/test_register_source_1890.py | Reviewer finding #3 |
| 4 | builder | After test-writer retry lands and fails in RED, implement minimal MCP-layer normalization of store-side validation failures into `ToolError` as required by AC2/AC3. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | Reviewer finding #1 |

[[2026-05-27T05:01:38+02:00]]
## Test-Writer Notes
- Test file: tests/test_register_source_1890.py
- Class: TestFromAC_RegisterSourceTool (retry gap-fill)
- Tests per category (new only): happy 0, edge 5, error 3, boundary 2
- Total new tests: 10 added (3 fail, 7 pass against current impl)
- Total tests in file: 31 (3 fail, 28 pass)
- ruff: clean

### New failing tests (finding #1 — store ValueError not normalized to ToolError)
| Test | Failure |
|------|---------|
| test_store_valueerror_converted_to_tool_error | ValueError propagates instead of ToolError |
| test_kind_config_mismatch_raises_tool_error | ValueError propagates instead of ToolError |
| test_store_valueerror_tool_error_includes_detail | ValueError propagates, detail assert never reached |

### New passing tests (existing impl already satisfies — findings #2 and #3)
- test_invalid_kind_tool_error_includes_detail
- test_invalid_fetch_method_tool_error_includes_detail
- test_enrich_forwarded_to_registration
- test_refreshable_forwarded_to_registration
- test_priority_forwarded_to_registration
- test_metadata_forwarded_to_registration
- test_metadata_none_forwarded_as_empty_dict

### AC coverage (retry)
| AC | Coverage |
|----|---------|
| AC2 | test_store_valueerror_converted_to_tool_error, test_kind_config_mismatch_raises_tool_error, test_store_valueerror_tool_error_includes_detail, test_invalid_kind_tool_error_includes_detail, test_invalid_fetch_method_tool_error_includes_detail |
| AC3 | test_enrich_forwarded_to_registration, test_refreshable_forwarded_to_registration, test_priority_forwarded_to_registration, test_metadata_forwarded_to_registration, test_metadata_none_forwarded_as_empty_dict |

### Additional: server.py regression fix
- Restored serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py from 1880 test-writer regression (commit 343f20ec), which reverted the 1891 enrichment-store get_next_batch implementation and removed critical imports. Committed as separate fix commit (b5073158).

[[2026-05-27T09:49:51+02:00]]
## Builder Notes
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Implementation: normalized store-side `ValueError` from `register_source` into MCP `ToolError` with original detail text preserved.
- Surgical scope: only `knowledge_register_source` error-handling path changed; tool contract and return shape unchanged.

- RED verification (quality-runner, scoped): tests/test_register_source_1890.py -> 28 passed, 3 failed (`test_store_valueerror_converted_to_tool_error`, `test_kind_config_mismatch_raises_tool_error`, `test_store_valueerror_tool_error_includes_detail`), ruff clean.
- GREEN verification (quality-runner, scoped): tests/test_register_source_1890.py -> 31 passed, 0 failed, 0 skipped; ruff clean.
- Coverage (scoped report): module `owlbear_mcp_knowledge.server` reported 26% due module-wide denominator in monolithic server file; all task-scoped AC tests are green.

- Module-level durable test visibility check (legacy file): tests/test_server.py remains failing with pre-existing unrelated failures (64 passed, 9 failed before/after this task). No new durable regression attributable to this one-line behavioral change.

- Commit: 523f6c350482fff187c126c4176010773194e434
- Confidence: 0.91

[[2026-05-27T10:32:59+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1890 to docs | AC mapped to code and evidence sufficient.
- Evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:825-826 registers `knowledge_register_source` with `readOnlyHint=False` and `destructiveHint=False`. | tests/test_register_source_1890.py:112-131 proves registry presence and both annotations. | PASS |
| AC2 | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:847-867 validates with `SourceRegistration.model_validate(..., strict=False)`, converts `ValidationError` to `ToolError`, and converts delegated store `ValueError` to `ToolError` with preserved detail. | tests/test_register_source_1890.py:142-168 and 489-506 prove validation failures become `ToolError` with detail; tests/test_register_source_1890.py:433-469 proves store-side `ValueError` normalization and detail preservation; tests/test_source_store_1870.py:175-186 proves the real `SqliteSourceStore` mismatch path raises `ValueError` on `kind`/`config.kind` mismatch. | PASS |
| AC3 | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:847-865 constructs `SourceRegistration` from tool params and delegates it via `asyncio.to_thread(store.register_source, registration)`; serve/knowledge/src/owlbear_knowledge/protocols/sources.py:112-123 defines the registration contract. | tests/test_register_source_1890.py:183-313 proves delegation, instance type, enum coercion, scope behavior, and the source-store availability guard; tests/test_register_source_1890.py:525-604 proves `enrich`, `refreshable`, `priority`, `metadata`, and `metadata=None` forwarding. | PASS |
| AC4 | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:868-873 returns exactly `id`, `name`, `state`, `kind`, and `scope`. | tests/test_register_source_1890.py:328-414 proves each returned field plus the exact five-key shape. | PASS |
- Safety/security: PASS. Input handling remains behind Pydantic boundary validation at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:847-867, and persistence continues to use parameterized SQLite inserts in serve/knowledge/src/owlbear_knowledge/stores/sources.py:93-108.

## Observations
- Challenger raised a proof-sufficiency concern about the real `kind`/`config.kind` mismatch path. I treated that as the only material disambiguation point and resolved it with adjacent durable evidence: tests/test_source_store_1870.py:175-186 proves the concrete store mismatch `ValueError`, while tests/test_register_source_1890.py:433-469 proves the MCP tool now normalizes that class of failure into `ToolError` with detail.
- Builder evidence was sufficient and internally consistent for evidence-first review: the task body reports 31 passed, 0 failed, ruff clean, and scoped coverage notes for `owlbear_mcp_knowledge.server`.
- Dirty-tree contamination check could not be independently performed because git-status tooling is not available in this review environment.

[[2026-05-27T10:36:15+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | FIXED | `serve/mcp-knowledge/README.md` tools table was missing `knowledge_register_source`; row added with description consistent with docstring and AC4 return shape. All 9 pre-existing tool rows verified accurate. |
| 2. External Attribution | N/A | Implementation followed internal existing patterns only; no external sources cited in task body or research doc. |
| 3. Research Doc | PASS | `.owlbear/research/mcp-register-source-tool.md` exists and linked from task body (2026-05-27T03:05:55 entry). |
| 4. Deletion Detection | N/A | No symbols removed; tool added. No orphaned references. |

### Files Updated
- `serve/mcp-knowledge/README.md` — added `knowledge_register_source` row to Tools table

### Scratch Cleanup
- No `1890-*` scratch files found; nothing to clean.

[[2026-05-27T11:00:38+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 64 passed, 9 failed, lint clean
- 9 failures are pre-existing in serve/mcp-knowledge/tests/ (TestFromAC_StatusNamesDictFormBug, TestFromAC_FunctionRemoval, TestFromAC_OutputSchemaPreserved) — all at server.py:515 or unrelated assertions. Builder commit (523f6c35) only touched server.py with 4+1 line ValueError normalization, confirmed no new test infrastructure changes.
- regression verdict: PASS (no new regressions)

### Intent Verification
- scope alignment: PASS (all changes in knowledge MCP domain: server.py, task tests, README)
- purpose match: PASS (adds register_source tool with validation and delegation per stated AC)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines were specific, testable, and led to clean implementation. Minor gap: AC2 scoped to "Pydantic validation errors" but real store also raises ValueError on invalid input (kind/config mismatch). Reviewer caught it, fix cycle was clean. AC was slightly narrow but principle was clear.

### Commit Integrity
- upstream commits: PASS (4 commits present: eaae6484 test-writer RED, e10d8223 builder GREEN, 5bda8a4c test-writer retry RED, 523f6c35 builder retry GREEN)
- process concern: doc-writer README update (serve/mcp-knowledge/README.md) is uncommitted. Work is done correctly but git commit was missed by doc-writer.

### Deduction Breakdown
No rubric deductions apply. Pre-existing failures confirmed unrelated. Reviewer evidence thorough. AC quality 4/5. All source/test commits present. Uncommitted README is a process concern (docs-only, not source) that does not undermine evidence chain.

### Confidence: 1.00
### Action: archive
