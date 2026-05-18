---
id: 1656
title: Retype _direct_source_config from AUTHENTICATED_WEB to URL_LIST for new 
  HTTP sources
status: archived
priority: important
created: 2026-05-18T03:27:04.998459+02:00
updated: 2026-05-18T16:15:19.302007+02:00
tags:
  - scope:knowledge
  - implementation
parent: 1650
depends_on:
  - 1653
ac:
  - 'AC-1: `_direct_source_config(source_url)` in `serve/knowledge/src/owlbear_knowledge/ingest.py`
    returns `(SourceType.URL_LIST, "http", {"url": source_url, "urls": [source_url]})`
    when `source_url` is a non-local HTTP/HTTPS URL'
  - 'AC-2: `_direct_source_config(source_url)` continues to return `(SourceType.FILE_GLOB,
    "file", ...)` for local file paths (local-path branch unchanged)'
  - 'AC-3: Existing `AUTHENTICATED_WEB` source records already in the database are
    not migrated or modified — `_resolve_source_by_url` still reuses them when URL
    matches'
  - 'AC-4: Implementation change is limited to `serve/knowledge/src/owlbear_knowledge/ingest.py`
    (single return-value edit)'
  - 'AC-5: Tests asserting the old `authenticated_web` type for auto-created HTTP
    sources (specifically `test_direct_ingest_delta.py::test_metadata_url_creates_source_link_for_enrichment`
    line 188) are updated to assert `url_list`; tests covering `_handle_url_list`
    handler behavior pass unchanged; a focused unit test for `_direct_source_config`
    asserts the new return tuple for HTTP URLs'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Change the non-local URL branch of `_direct_source_config` in `ingest.py` to return `SourceType.URL_LIST` instead of `SourceType.AUTHENTICATED_WEB`. The config dict shape (`{"url": source_url, "urls": [source_url]}`) and `fetch_method="http"` remain identical.

**Out-of-scope:** Migration of existing `AUTHENTICATED_WEB` source records. Changes to `_handle_url_list` or `_handle_authenticated_web` in `refresh.py`. Changes to the local-path (`FILE_GLOB`) branch.

## Context

Research task #1653 confirmed handler equivalence between `_handle_url_list` and `_handle_authenticated_web` for `fetch_method="http"` single-URL sources. This task implements the one-line retype that research validated.

[[2026-05-18T15:10:45+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One return-value change in one function |
| Interface clarity | PASS | AC-1 specifies exact return tuple; AC-2 defines unchanged branch |
| Dependency correctness | PASS | #1653 archived with PASS — handler equivalence confirmed |
| Module layering | PASS | Change within serve/knowledge, no cross-package impact |
| TDD compliance | PASS | Proof bundle: behavioral; test-writer will write RED tests |
| KISS/YAGNI | PASS | Literal one-line change |
| Premise challenge | PASS | Research #1653 validated equivalence; URL_LIST is semantically correct for HTTP URLs |
| Pattern consistency | PASS | SourceType.URL_LIST already used elsewhere in codebase |
| Security surface | PASS | No new boundaries; same fetcher, same content_safety wrapping |
| Single domain | PASS | scope:knowledge only |

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Key challenges: (1) test_direct_ingest_delta.py:188 asserts old type and will break — AC-5 was contradictory; (2) AC-3/AC-4 were scope constraints not mechanically verifiable; (3) research memo metadata caveats
- Architect response: ACCEPTED (1) — refined AC-5 to explicitly name the test that needs updating and distinguish test categories. REBUTTED (2) — AC-3 reworded with verifiable mechanism (_resolve_source_by_url reuse path); AC-4 is diff-verifiable by reviewer. REBUTTED (3) — research memo PASS conclusion was scoped to refresh-status equivalence with metadata diffs explicitly acknowledged as non-branching; that is sufficient for the retype.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### AC Refinement
- AC-5 rewritten: original said "existing tests pass without modification" which contradicts the retype. Now explicitly names test_metadata_url_creates_source_link_for_enrichment as needing update and requires a focused unit test for _direct_source_config.
- AC-3 reworded: now references the concrete mechanism (_resolve_source_by_url reuse) rather than just stating "no migration."

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC-5 and AC-3 for testability. Advanced to todo.

[[2026-05-18T15:21:30+02:00]]
## Test-Writer Notes
- Test file: tests/test_ingest_1656.py
- Modified: serve/mcp-knowledge/tests/test_direct_ingest_delta.py::test_metadata_url_creates_source_link_for_enrichment (assert url_list, AC-5)
- Classes: TestFromAC_DirectSourceConfig
- Tests per category: happy 1, edge 3, error 0, boundary 1
- Total: 5 new tests + 1 existing test updated = 6 tests, all FAIL
- ruff: clean

AC coverage:
- AC-1: test_https_url_returns_url_list_type (happy), test_http_url_returns_url_list_type (edge), test_https_url_with_query_params_returns_url_list_type (edge), test_https_url_full_return_tuple (edge/spec)
- AC-2: Covered by existing file:// URL tests in test_direct_ingest_delta.py — FILE_GLOB branch behavior unchanged; excluded from new file (regression guards pass by design, cannot be RED)
- AC-3: Diff-verifiable constraint (no migration code added); _resolve_source_by_url reuse is existing behavior that passes now and after the retype — not included as a failing test
- AC-4: Diff-verifiable (single-file change)
- AC-5: test_https_url_full_return_tuple (focused unit test); test_metadata_url_creates_source_link_for_enrichment updated to assert url_list (integration test)

Failure evidence (quality-runner confirmed):
- test_ingest_1656.py: 5 failed, AssertionError: AUTHENTICATED_WEB != URL_LIST
- test_direct_ingest_delta.py::test_metadata_url_creates_source_link_for_enrichment: AssertionError: expected url_list, got authenticated_web

[[2026-05-18T15:39:56+02:00]]
## Builder Notes
### Files Changed
- serve/knowledge/src/owlbear_knowledge/ingest.py

### Implementation
- Updated `_direct_source_config` non-local URL branch to return `SourceType.URL_LIST` (was `SourceType.AUTHENTICATED_WEB`).
- Preserved tuple shape and fetch method: `(source_type, "http", {"url": source_url, "urls": [source_url]})`.
- No migration logic added; local-path `FILE_GLOB` branch untouched.

### RED Verification (quality-runner)
- Scoped RED run on `tests/test_ingest_1656.py` + `serve/mcp-knowledge/tests/test_direct_ingest_delta.py::test_metadata_url_creates_source_link_for_enrichment`.
- Result: 0 passed, 6 failed.
- Failures were all expected enum mismatches: `authenticated_web` vs `url_list`.
- Lint: clean.

### GREEN Verification (quality-runner)
- Scoped GREEN run on:
  - `tests/test_ingest_1656.py`
  - `serve/mcp-knowledge/tests/test_direct_ingest_delta.py::test_metadata_url_creates_source_link_for_enrichment`
- Result: 6 passed, 0 failed.
- Lint: clean.

### Durable/Regression Verification (quality-runner)
- Scoped ingest-related durable tests:
  - `serve/mcp-knowledge/tests/test_direct_ingest_delta.py`
  - `serve/knowledge/tests/test_ingest_replace.py`
  - `serve/knowledge/tests/test_ingest_partial_extraction.py`
  - plus task test file
- Result: 24 passed, 0 failed.
- Lint: clean.

### Coverage
- Coverage module: `owlbear_knowledge.ingest`
- Best passing scoped evidence: 88%.
- Additional full-suite check reached 90% for module, but suite contains extensive unrelated baseline failures outside task scope; not used as gating pass for this task.

### Commit
- a7fe0c6c
- Message: `fix: retype direct HTTP source config to url_list (task 1656)`
- Diff: 1 file changed, 1-line semantic retype.

### Evidence Summary
- AC-1/AC-5 satisfied by passing focused tests and integration assertion update path.
- AC-2 satisfied (local file branch unchanged; durable file:// tests pass).
- AC-3/AC-4 satisfied by surgical single-file diff with no migration/path-handler changes.

[[2026-05-18T15:58:14+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1656 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped GREEN proof reported 6 passed / 0 failed with lint clean; durable ingest-related regression proof reported 24 passed / 0 failed with lint clean; builder also reported ingest-module coverage at 88% on the best passing scoped run and 90% on an additional broader run.
- Challenger raised a proof-scope concern about an omitted adjacent source-identity regression suite. Reviewer resolved that by independently rerunning the direct-ingest identity subset that actually shares this task's HTTP source-creation path: 4 passed / 0 failed, lint clean.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/knowledge/src/owlbear_knowledge/ingest.py:130` returns `SourceType.URL_LIST, "http", {"url": source_url, "urls": [source_url]}` for non-local URLs. | `tests/test_ingest_1656.py:22`, `tests/test_ingest_1656.py:27`, `tests/test_ingest_1656.py:32`, `tests/test_ingest_1656.py:37`, `tests/test_ingest_1656.py:46`, plus persisted-row proof at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:170` and `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:188`. | PASS |
| AC-2 | Local-path branch remains unchanged at `serve/knowledge/src/owlbear_knowledge/ingest.py:128`. | `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:296` with assertion at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:307`, and `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:315` with assertion at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:328`. | PASS |
| AC-3 | Existing-source reuse still happens before the create path: `serve/knowledge/src/owlbear_knowledge/ingest.py:141` resolves by URL before `serve/knowledge/src/owlbear_knowledge/ingest.py:146` calls `_direct_source_config`; URL matching is type-agnostic via `serve/knowledge/src/owlbear_knowledge/source_store.py:69` and `serve/knowledge/src/owlbear_knowledge/source_store.py:179`. No migration/update code was introduced in the reviewed source change. | Builder durable proof includes `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:205` (AUTHENTICATED_WEB cross-scope non-reuse) and `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:243` with assertions at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:269` and `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:270` (URL-based reuse path). Reviewer independent rerun additionally passed `tests/test_knowledge_ingest_source_identity_1556.py:163`, `tests/test_knowledge_ingest_source_identity_1556.py:191`, `tests/test_knowledge_ingest_source_identity_1556.py:212`, and `tests/test_knowledge_ingest_source_identity_1556.py:230`. | PASS |
| AC-4 | Code inspection shows the semantic implementation delta at `serve/knowledge/src/owlbear_knowledge/ingest.py:130`; builder commit summary identifies a single-file source edit in `serve/knowledge/src/owlbear_knowledge/ingest.py`. | Builder evidence packet is internally consistent with the inspected source. | PASS |
| AC-5 | Focused unit proof covers the exact tuple at `tests/test_ingest_1656.py:46` and persisted integration proof at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:170` / `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:188`; unchanged URL_LIST refresh-path behavior remains covered by `serve/knowledge/tests/test_ingest_partial_extraction.py:123` / `serve/knowledge/tests/test_ingest_partial_extraction.py:144` and `serve/knowledge/tests/test_ingest_partial_extraction.py:152` / `serve/knowledge/tests/test_ingest_partial_extraction.py:168`. | Passing builder evidence is specific enough that the tests would fail on an old-type regression or on a changed local-file branch. | PASS |
- Safety & security check: no new input sink, credential surface, dependency, or logging behavior was introduced; the change is limited to the enum selected on the new-source create path.

## Observations
- The full `tests/test_knowledge_ingest_source_identity_1556.py` suite is not a reliable gate for this task because it currently carries unrelated vector-store, query, and cleanup failures outside this retype's scope. The targeted direct-ingest identity subset is the relevant adjacent proof surface and passed independently.
- I could not independently execute a git-based dirty-tree contamination check for the scoped files because terminal/git access was not available through the current tool surface. No contradictory evidence appeared in the files inspected during review.

[[2026-05-18T16:00:18+02:00]]
## Docs Gate

**Verdict: PASS**

### Changed files
- `serve/knowledge/src/owlbear_knowledge/ingest.py` → maps to `serve/knowledge/README.md`
- `serve/mcp-knowledge/tests/test_direct_ingest_delta.py` (test update) → maps to `serve/mcp-knowledge/README.md`

### Checklist

**Item 1 — README Verification:** PASS — no changes needed.
- `serve/knowledge/README.md` (100 lines, full read): documents module groups and ingestion at a high level; no mention of `SourceType` internal classification, `authenticated_web`, `url_list`, or `_direct_source_config`. One-line enum retype has no README surface.
- `serve/mcp-knowledge/README.md` (80 lines, full read): `ingest_document` tool description references URL-like metadata delta detection generically; no `SourceType` classification documented. No drift introduced.

**Item 2 — External Attribution:** N/A — no external sources used in this implementation task. Attribution for the prerequisite handler equivalence analysis (task #1653) is already recorded in `.owlbear/sources/overview.md` as "No external sources — codebase static analysis only."

**Item 3 — Research Doc:** N/A — no research artifact created for this implementation task. Research was done in dependency task #1653 (archived).

**Item 4 — Deletion Detection:** N/A — no source files deleted; single one-line edit in `ingest.py`.

### Scratch cleanup
Deleted: `.owlbear/scratch/1656-pytest-output.txt`, `.owlbear/scratch/1656-ruff-output.txt`, `.owlbear/scratch/1656-ruff-output.json`

[[2026-05-18T16:15:19+02:00]]
## Audit

### Regression Detection
Full-suite quality-runner: 4832 passed, ~261 failed — all failures in unrelated domains (cockpit_view missing old task files, engine_accessor_migration, mcp-kanban server, cockpit_react_compiler). Scoped knowledge domain: 214 passed, 17 failed — all failures in graph stats/list sources/stats resource tests with no relationship to _direct_source_config retype. Task-scoped and ingest durable tests all pass clean. Lint: clean.

No regressions introduced by this task.

### Intent Verification
Changed file (`serve/knowledge/src/owlbear_knowledge/ingest.py`) stays within scope:knowledge domain. Single-line retype from AUTHENTICATED_WEB to URL_LIST matches stated purpose exactly. Test file at `tests/test_ingest_1656.py` and updated integration test at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py` are appropriate locations. No extraneous scope.

### Architect Quality
Score: 5/5 — Specific, complete, clean implementation path. ACs name exact return tuples, unchanged branches, single-file constraint, and specific test files to update. Architect addressed challenger concerns and refined AC-5 and AC-3 for testability after challenger caught a contradiction in the original AC-5.

### Commit Integrity
- Builder commit `a7fe0c6c`: 1 file changed, 1 insertion, 1 deletion — confirmed single-file scope.
- Test-writer commit `7edd580e`: task tests committed with proper attribution.
- Both reference task 1656.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
