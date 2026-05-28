---
id: 1909
title: 'Knowledge: Implement CompositeSourceFetcher adapter'
status: review
priority: needed
created: 2026-05-28T01:41:35.432412+02:00
updated: 2026-05-28T04:02:40.196485+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent: 1904
depends_on: []
ac:
  - 'AC1: CompositeSourceFetcher satisfies SourceFetcher protocol (isinstance check
    passes)'
  - 'AC2: CompositeSourceFetcher.fetch_source(source) where source.kind=URL_LIST —
    iterates config.urls, returns FetchResult with one FetchedDocument per successfully
    fetched url (title=url, text=content, uri=url) and one FetchError per failed url'
  - 'AC3: CompositeSourceFetcher.fetch_source(source) where source.kind=FILE_GLOB
    — resolves each pattern in config.patterns relative to config.base_path, deduplicates
    resolved paths, returns FetchResult with one FetchedDocument per readable file'
  - 'AC4: CompositeSourceFetcher.fetch_source(source) where source.kind=AUTHENTICATED_WEB
    — calls content_fetcher_factory(source.fetch_method) to obtain ContentFetcher,
    invokes fetcher.fetch(config.base_url), returns FetchResult with one FetchedDocument
    (title=base_url, text=fetched content, uri=base_url)'
  - 'AC5: CompositeSourceFetcher.fetch_source(source) where source.kind=INLINE — returns
    FetchResult(documents=(), errors=())'
  - 'AC6: CompositeSourceFetcher.fetch_source — when cancel.is_set() returns True
    between iteration items, stops iteration and returns FetchResult containing documents
    collected so far'
  - 'AC7: CompositeSourceFetcher.fetch_source — item-level exceptions (httpx.HTTPStatusError,
    FileNotFoundError, PermissionError, ContentFetcher failures) are caught and appended
    as FetchError(uri=source_uri, error=str(exc)); the method never raises'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Create `serve/knowledge/src/owlbear_knowledge/source_fetcher.py` implementing the `SourceFetcher` protocol from `protocols/fetcher.py`.

## Details
- Single class `CompositeSourceFetcher` dispatches by `source.kind`:
  - URL_LIST → iterate urls with intake.read_url
  - FILE_GLOB → glob patterns with intake.read_file
  - AUTHENTICATED_WEB → content_fetcher.fetch(base_url)
  - INLINE → empty FetchResult
- Constructor: `workspace_root: Path`, `content_fetcher_factory: Callable[[FetchTransport], ContentFetcher]`
- Per-item exceptions caught as FetchError, never raises
- Cancel signal checked between iteration items
- FILE_GLOB: deduplicate resolved paths across multiple patterns; respect follow_symlinks
- Map IntakeResult → FetchedDocument (title=source_url or filename, text=content, uri=source_path_or_url)
- ~120 LOC target
- Research: .owlbear/research/source-fetcher-adapter-b2b.md
- Depends on: nothing (protocol already exists)

[[2026-05-28T02:16:20+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One class, one protocol, one dispatch table |
| Interface clarity | PASS | AC refined to name fetch_source + concrete I/O per kind |
| Dependency correctness | PASS | No deps needed — protocol, intake, cancellation all exist |
| Module layering | PASS | All imports within owlbear_knowledge; no upward imports |
| TDD compliance | PASS | Test-writer creates tests at todo via standard pipeline |
| KISS/YAGNI | PASS | Option A (single dispatch class ~120 LOC) is simplest viable. Deletion test: removing adapter forces IngestCoordinator to inline I/O dispatch — worse separation |
| Premise challenge | PASS | SourceFetcher protocol has zero implementations; IngestCoordinator.refresh() requires one |
| Pattern consistency | PASS | Follows existing protocol + BoundaryModel + async patterns in knowledge package |
| Security surface | PASS | URL_LIST uses intake.read_url (SSRF-protected via _ssrf.check_url_allowed). FILE_GLOB uses sandbox_path. AUTHENTICATED_WEB delegates to injected ContentFetcher — browser SSRF is browser package's responsibility, not this adapter |
| Single domain | PASS | knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| URL fetch | Network error/4xx/5xx | httpx.HTTPStatusError | Yes → FetchError | Partial results, error reported |
| File read | Missing file | FileNotFoundError | Yes → FetchError | Skipped file, error reported |
| File read | Path escapes sandbox | PermissionError | Yes → FetchError | Skipped file, error reported |
| Auth web fetch | ContentFetcher failure | Exception | Yes → FetchError | Source not refreshed |
| Glob resolution | Invalid pattern | OSError | Yes → FetchError | Pattern skipped |

### Design Diverge
- Trigger: skipped — research already evaluated 3 options (A: single dispatch, B: strategy per-kind, C: wrap legacy). Option A dominates on KISS, LOC, and enables full legacy removal.

### Challenge Results
- Challenger: reconsider (0.11)
- Findings: (1) \"missing implementation artifact\" — invalid, this is backlog not in-progress; (2) AC quality B1/B2/B3 issues — valid, AC refined; (3) consolidation-test gap — rebutted: #1911 is the integration/wiring task depending on both #1909 and #1910; (4) AUTHENTICATED_WEB security — noted but out of scope for this adapter
- Architect response: accepted AC quality findings (refined all 7 AC lines), rebutted remaining findings with justification

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC lines for h-ac-quality compliance (B1: named fetch_source in AC2-7; B2: explicit I/O pairs in AC4/AC6; B3: eliminated naked quantifiers). Set proof_bundle=behavioral. Advanced to todo.

[[2026-05-28T02:42:18+02:00]]
## Test-Writer Notes
- Test file: tests/test_source_fetcher_1909.py
- Classes: TestFromAC_CompositeSourceFetcher
- Tests per category: happy 20, edge 3, error 11, boundary 3
- Total: 37 tests, all FAIL (ImportError — owlbear_knowledge.source_fetcher does not exist)
- ruff: clean

## AC Coverage
| AC | Tests |
|----|-------|
| AC1 — isinstance SourceFetcher | test_isinstance_source_fetcher_protocol |
| AC2 — URL_LIST dispatch | test_url_list_single_url_returns_one_document, test_url_list_document_title_equals_url, test_url_list_document_text_equals_fetched_content, test_url_list_document_uri_equals_url, test_url_list_multiple_urls_returns_one_document_per_url, test_url_list_empty_urls_returns_empty_fetch_result, test_url_list_failed_url_captured_as_fetch_error, test_url_list_fetch_error_uri_equals_failed_url, test_url_list_fetch_error_message_equals_str_exception, test_url_list_batch_continues_after_url_failure |
| AC3 — FILE_GLOB dispatch | test_file_glob_single_pattern_*, test_file_glob_document_text_*, test_file_glob_pattern_matching_no_files_*, test_file_glob_multiple_patterns_*, test_file_glob_deduplicates_paths_*, test_file_glob_file_not_found_*, test_file_glob_permission_error_* |
| AC4 — AUTHENTICATED_WEB | test_auth_web_calls_factory_*, test_auth_web_calls_content_fetcher_*, test_auth_web_returns_exactly_one_document, test_auth_web_document_title_*, test_auth_web_document_text_*, test_auth_web_document_uri_*, test_auth_web_content_fetcher_failure_*, test_auth_web_fetch_error_uri_* |
| AC5 — INLINE | test_inline_returns_fetch_result_instance, test_inline_documents_tuple_is_empty, test_inline_errors_tuple_is_empty |
| AC6 — Cancellation | test_cancel_stops_url_iteration_*, test_cancel_returns_partial_results_*, test_cancel_none_processes_all_urls, test_cancel_stops_file_glob_iteration_* |
| AC7 — Never raises | test_http_status_error_caught_*, test_file_not_found_error_caught_*, test_permission_error_caught_*, test_content_fetcher_exception_caught_*, test_url_fetch_error_error_field_* |

## Patch strategy
URL/FILE_GLOB item-level error tests use `patch("owlbear_knowledge.source_fetcher.intake.read_url")` / `.read_file` — assumes `from owlbear_knowledge import intake` import pattern. FILE_GLOB happy-path tests use real files via tmp_path.

[[2026-05-28T02:59:24+02:00]]
## Builder Notes
- Implementation: added `serve/knowledge/src/owlbear_knowledge/source_fetcher.py` with `CompositeSourceFetcher` implementing `SourceFetcher`.
- Dispatch behavior: `fetch_source` routes by `source.kind` (`URL_LIST`, `FILE_GLOB`, `AUTHENTICATED_WEB`, `INLINE`) and returns `FetchResult` for each path.
- URL_LIST: iterates `config.urls`, checks `cancel.is_set()` between items, maps each successful `intake.read_url` result to `FetchedDocument(title=url, text=content, uri=url)`, and captures per-url exceptions as `FetchError`.
- FILE_GLOB: resolves `config.base_path` via `sandbox_path`, iterates each glob pattern, deduplicates files by resolved path across patterns, respects `follow_symlinks`, checks cancellation between items, reads with `intake.read_file`, maps to `FetchedDocument(title=filename, text=content, uri=source_path)`, captures per-item/per-pattern failures as `FetchError`.
- AUTHENTICATED_WEB: calls `content_fetcher_factory(source.fetch_method)`, invokes `fetcher.fetch(config.base_url)`, returns one mapped document or one `FetchError` on failure.
- Never-raise guarantee: dispatch has a top-level fallback returning `FetchError(uri=source.id, error=str(exc))` for unexpected failures.
- Tests (quality-runner, scoped): `tests/test_source_fetcher_1909.py` -> 38 passed, 0 failed, 0 skipped.
- Coverage (quality-runner, scoped): `source_fetcher` 90%.
- Lint (quality-runner): clean (`ruff` clean=true; violations=[]).
- Module-level durable test check: no module-level `source_fetcher` test file exists; skipped per GREEN workflow.
- Commit: `81517475` — `feat: implement composite source fetcher adapter (#1909, builder)`.

### Post-task Reflection
- Problem faced: initial lint run failed on import sorting and type-checking-only import placement (`I001`, `TC001`, `TC003`).
- Workaround applied: moved annotation-only imports to a `TYPE_CHECKING` block and let Ruff apply canonical import ordering.
- Pattern discovered: task tests patch `owlbear_knowledge.source_fetcher.intake.read_*`, so module-level `intake` import is required for stable patch targets.
- Quality gap: only task-scoped tests exist for this module; no durable module-level test file currently provides long-term regression coverage.

[[2026-05-28T03:56:14+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: task notes report quality-runner scoped tests passed (38), source_fetcher coverage 90%, and ruff clean; direct source inspection is consistent with the claimed implementation.
- Challenger cross-check: proceed (0.84). The challenge narrowed the rationale to insufficient executable proof rather than an observed implementation defect.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3 | No task test exercises a non-default config.base_path, so the suite would not fail if FILE_GLOB ignored base_path and always globbed from workspace_root. | serve/knowledge/src/owlbear_knowledge/source_fetcher.py:100,106,111; tests/test_source_fetcher_1909.py:75,77,84,335,344,352,364,374,384,400,578,618,632 | todo |
| 2 | AC7 | FILE_GLOB and AUTHENTICATED_WEB failure tests do not fully assert the required FetchError payload. FILE_GLOB error cases only prove that an error exists, and AUTHENTICATED_WEB failure cases omit error=str(exc). | serve/knowledge/src/owlbear_knowledge/source_fetcher.py:125,148; tests/test_source_fetcher_1909.py:379,391,395,407,463,469,473,479,614,625,628,639 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a FILE_GLOB test using a non-default base_path and prove globbing is relative to that directory rather than workspace root. | tests/test_source_fetcher_1909.py | AC3 gap from tests/test_source_fetcher_1909.py:75,77,84,335,344,352,364,374,384,400,578,618,632 against serve/knowledge/src/owlbear_knowledge/source_fetcher.py:100,106,111 |
| 2 | test-writer | Strengthen FILE_GLOB and AUTHENTICATED_WEB failure tests to assert FetchError.uri and FetchError.error exactly match the AC7 contract. | tests/test_source_fetcher_1909.py | AC7 gap from tests/test_source_fetcher_1909.py:379,391,395,407,463,469,473,479,614,625,628,639 against serve/knowledge/src/owlbear_knowledge/source_fetcher.py:125,148 |

## Observations
- Direct code review did not uncover a blocking implementation defect in serve/knowledge/src/owlbear_knowledge/source_fetcher.py; the rejection is for insufficient proof on AC3 and AC7.
- No adjacent durable source_fetcher test surface was found in tests/, so the task-local gaps are not covered elsewhere.

[[2026-05-28T04:02:40+02:00]]
## Test-Writer Notes
- Retry: added 4 tests for reviewer gaps (AC3 + AC7). All pass against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: tests/test_source_fetcher_1909.py
- Classes: TestFromAC_CompositeSourceFetcher
- New tests added (4):
  - AC3 gap: test_file_glob_non_default_base_path_globs_relative_to_base_path — creates 2 txt files at workspace root + 1 in 'docs/' subdir; asserts base_path="docs" yields exactly 1 document (proves glob is relative to base_path, not workspace_root)
  - AC7 gap (FILE_GLOB FileNotFoundError): test_file_glob_file_not_found_fetch_error_uri_and_error_exact — asserts FetchError.uri == str(resolved path) and FetchError.error == str(exc)
  - AC7 gap (FILE_GLOB PermissionError): test_file_glob_permission_error_fetch_error_uri_and_error_exact — same exact-payload assertion for PermissionError
  - AC7 gap (AUTHENTICATED_WEB): test_auth_web_fetch_error_error_equals_str_of_exception — asserts FetchError.error == str(exc)
- Quality-runner (scoped): 42 passed, 0 failed, 0 skipped; ruff clean
- Commit: 867e59cc
