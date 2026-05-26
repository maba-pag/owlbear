---
id: 1885
title: 'Knowledge: ContentFetcher protocol — fetch abstraction for refresh'
status: todo
priority: needed
created: 2026-05-26T06:08:59.378851+02:00
updated: 2026-05-26T09:25:43.274108+02:00
tags:
  - knowledge
  - layer-2
parent: 1877
depends_on: []
ac:
  - 'File `protocols/fetcher.py` defines `FetchedDocument(BoundaryModel)` with required
    fields `title: str`, `text: str`, `uri: str` and optional `external_id: str |
    None = None`, `metadata: Metadata = Field(default_factory=dict)`'
  - 'Same file defines `FetchError(BoundaryModel)` with required fields `uri: str`,
    `error: str`'
  - 'Same file defines `FetchResult(BoundaryModel)` with `documents: tuple[FetchedDocument,
    ...] = Field(default_factory=tuple)` and `errors: tuple[FetchError, ...] = Field(default_factory=tuple)`'
  - '`@runtime_checkable class SourceFetcher(Protocol)` with `async def fetch_source(self,
    source: ConfiguredSourceRecord, *, cancel: CancelSignal | None = None) -> FetchResult`'
  - 'SourceFetcher.fetch_source docstring: Guarantees (partial documents on cancel;
    per-item failures in errors tuple, never raised); Non-guarantees (ordering, batch
    strategy); Side effects (transport I/O); Raises (never)'
  - All public names (`FetchedDocument`, `FetchError`, `FetchResult`, 
    `SourceFetcher`) added to `protocols/__init__.py` grouped import from 
    `.fetcher` AND listed in `__all__`
  - 'Module imports only: `.common` (BoundaryModel, Metadata), `.sources` (ConfiguredSourceRecord),
    `owlbear_knowledge.cancellation` (CancelSignal), stdlib, pydantic — no other knowledge
    imports'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Define a ContentFetcher protocol that IngestCoordinator.refresh() can use to retrieve content from registered sources. Must support filesystem, HTTP, and browser transports.

## Context

- Legacy: `serve/knowledge/src/owlbear_knowledge/refresh.py` uses an injected `content_fetcher` object
- Protocol location: `serve/knowledge/src/owlbear_knowledge/protocols/` (new file)
- Gap identified in: `.owlbear/research/1877-ingest-coordinator.md`
- SourceKind determines transport: FILE_GLOB→filesystem, URL_LIST→HTTP, AUTHENTICATED_WEB→browser

[[2026-05-26T06:40:47+02:00]]
## Research

Key findings:
- Protocol named `SourceFetcher` (avoids legacy `ContentFetcher` collision)
- `fetch_source(source, cancel) -> FetchResult` — source-aware, per-item error accounting, cancel-aware
- `FetchedDocument.uri` required (replacement identity for Content dedup)
- `FetchResult` wrapper carries `documents` + `errors` tuples
- Registry injection: `Mapping[FetchTransport, SourceFetcher]` on coordinator
- INLINE/NONE handled by coordinator directly (no fetcher)
- Three transport impls: FilesystemFetcher, HttpFetcher, BrowserFetcher
- Challenger forced rename, cancel param addition, required uri, error wrapper (revised from .34 to .80 confidence)

Doc: `.owlbear/research/1885-contentfetcher-protocol.md`
Follow-up: #1886 (already exists, depends on this task + #1884)

[[2026-05-26T07:02:16+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single protocol file defining one fetcher abstraction |
| Interface clarity | PASS | After AC rewrite: precise field types, contract docstring required, import boundary explicit |
| Dependency correctness | PASS | No deps needed — greenfield protocol definition; #1886 depends on this (correct direction) |
| Module layering | PASS | protocols/ package is the designated boundary surface; imports only from .common, .sources, cancellation |
| TDD compliance | PASS | Greenfield; test-writer creates smoke tests for type construction + protocol checkability |
| KISS/YAGNI | PASS | Minimal types (3 models + 1 protocol); no speculative features |
| Premise challenge | PASS | Protocol required by IngestCoordinator.refresh() (#1877 AC8 stub); research validated need |
| Pattern consistency | PASS | BoundaryModel base, @runtime_checkable, tuple returns, Guarantees/Non-guarantees docstring — all match existing protocols |
| Security surface | PASS | Internal protocol; no system boundaries; transport I/O is implementation-level (not here) |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
N/A — pure type/protocol definition, no runtime logic.

### Design Diverge
- Trigger: skipped — single clear approach from research (Option B won evaluation at .85 weighted score)

### Challenge Results
- Challenger: block (confidence 0.41)
- Key findings: (1) AC6 dependency contradiction — critical, ACCEPTED (rewrote to explicit allowed-import list); (2) missing contract semantics in method — moderate, ACCEPTED (added docstring requirement AC5); (3) public surface ambiguity — moderate, ACCEPTED (specified __all__ membership in AC6); (4) naming drift in title — moderate, DECLINED (title cosmetic; AC unambiguously names SourceFetcher); (5) consolidation-test gap — minor, DECLINED (#1886 serves as integration validation)
- Architect response: accepted 3/5 findings; rewrote all AC from scratch addressing contradictions

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Wrote 7 precise AC lines (task had none). Addressed challenger findings: fixed dependency constraint contradiction, added contract-semantics requirement, specified __all__ membership. Proof bundle set to smoke. Advanced to todo.

[[2026-05-26T07:29:48+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_fetcher_protocol_1885.py`
**Proof bundle:** smoke (one test per AC line)

**Classes:**
- `TestFromAC_FetchedDocumentModel` — AC1
- `TestFromAC_FetchErrorModel` — AC2
- `TestFromAC_FetchResultModel` — AC3
- `TestFromAC_SourceFetcherProtocol` — AC4
- `TestFromAC_SourceFetcherDocstring` — AC5
- `TestFromAC_ProtocolsInitReexport` — AC6
- `TestFromAC_FetcherModuleImports` — AC7

**Test counts by category:** 7 smoke tests (1 per AC line), happy path only

**Fail confirmation:** pytest exit 1 — `ModuleNotFoundError: No module named 'owlbear_knowledge.protocols.fetcher'` (collection error; all 7 tests fail as expected for greenfield module). Lint: clean (ruff exit 0).

**AC coverage table:**
| AC | Test | Status |
|----|------|--------|
| AC1 FetchedDocument fields | `test_fetched_document_required_fields_and_optional_defaults` | FAIL (ImportError) |
| AC2 FetchError fields | `test_fetch_error_required_fields` | FAIL (ImportError) |
| AC3 FetchResult defaults | `test_fetch_result_empty_defaults` | FAIL (ImportError) |
| AC4 runtime_checkable protocol | `test_source_fetcher_is_runtime_checkable` | FAIL (ImportError) |
| AC5 docstring sections | `test_fetch_source_docstring_contains_required_sections` | FAIL (ImportError) |
| AC6 __init__.py + __all__ | `test_all_public_names_in_protocols_namespace_and_all` | FAIL (ImportError) |
| AC7 import constraints | `test_fetcher_module_imports_only_from_allowed_sources` | FAIL (ImportError) |

[[2026-05-26T07:56:16+02:00]]
## Builder Notes

### Plan
- Add new protocol module at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` implementing AC1-AC5 and AC7 import constraints.
- Re-export fetcher public surface in `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py` for AC6.
- Validate via quality-runner scoped test/lint/coverage for task file `tests/test_fetcher_protocol_1885.py`.

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` (new)
- `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py` (updated re-exports and sorted `__all__`/imports)

### RED Verification
- quality-runner (scoped): `tests/test_fetcher_protocol_1885.py`
- Result: collection error `ModuleNotFoundError: No module named 'owlbear_knowledge.protocols.fetcher'` (expected RED)
- Lint on test file: clean

### GREEN Implementation
- Added `FetchedDocument(BoundaryModel)` with required `title`, `text`, `uri`; optional `external_id`, `metadata` default factory.
- Added `FetchError(BoundaryModel)` with required `uri`, `error`.
- Added `FetchResult(BoundaryModel)` with tuple defaults for `documents` and `errors`.
- Added `@runtime_checkable SourceFetcher(Protocol)` with async signature:
  `fetch_source(source: ConfiguredSourceRecord, *, cancel: CancelSignal | None = None) -> FetchResult`.
- Added required docstring sections on `fetch_source`: Guarantees, Non-guarantees, Side effects, Raises.
- Re-exported `FetchedDocument`, `FetchError`, `FetchResult`, `SourceFetcher` from protocols package and added to `__all__`.
- Kept fetcher imports constrained to allowed sources/stdlib/pydantic; moved type-only imports under `TYPE_CHECKING` to satisfy lint.

### Verification Evidence (quality-runner)
- Scoped tests: passed 7, failed 0, skipped 0
- Lint: clean true, violations []
- Coverage module `owlbear_knowledge.protocols.fetcher`: 100%
- Exit codes: pytest 0, ruff 0

### Durable Module-Level Test File Check
- Checked for module-level durable file `**/test_fetcher_protocol.py`: none found.
- Recorded as: No module-level test file — skip.

### Commit
- `707ec2ea0c489ce4a34ce907fb778a0d443c210e`
- Message: `feat: add source fetcher protocol boundary (#1885, builder)`

### Fixes Applied During Verification
- Initial lint issues resolved:
  - `RUF022` (`__all__` sorting) in protocols init
  - `I001` import sorting in protocols init
  - `TC001` type-checking import placement in fetcher module
- Re-ran full scoped gate after fixes; final gate clean.

[[2026-05-26T08:15:50+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1885 -> todo | Implementation matches the AC, but proof is insufficient for AC1-AC5 and AC7.
- Builder evidence reviewed first: scoped quality-runner summary reports 7 passing tests, clean lint, and 100% coverage for `owlbear_knowledge.protocols.fetcher`; current editor diagnostics also show no errors in the changed files.
- Direct code inspection confirms the implementation currently satisfies the contract in `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` and the re-export surface in `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1-AC3 | The smoke tests prove field values/defaults only; they do not assert that `FetchedDocument`, `FetchError`, and `FetchResult` inherit `BoundaryModel`, so the boundary-model contract can regress without failing the suite. | Models inherit `BoundaryModel` at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:20`, `:30`, `:37`. Tests only assert constructed values/defaults at `tests/test_fetcher_protocol_1885.py:62-66`, `:78-79`, `:91-92`. | todo |
| 2 | AC4 | The protocol test only checks `isinstance(_FakeFetcher(), SourceFetcher)` on a duck-typed fake; it does not prove the required async `fetch_source(source, *, cancel)` signature or return contract. | Required method contract is defined at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:48-53`. Test body at `tests/test_fetcher_protocol_1885.py:101-113` uses a fake fetcher and a single `isinstance(...)` assertion. | todo |
| 3 | AC5 | The docstring test only checks section headings, not the required semantics inside those sections (partial documents on cancel, per-item failures in `errors`, never raised, ordering/batch strategy non-guarantees, transport I/O, raises never). | Required docstring semantics appear at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:56-69`. Test only loops over headings at `tests/test_fetcher_protocol_1885.py:124-127`. | todo |
| 4 | AC7 | The import-boundary test checks only a short forbidden list; it does not assert the full allowlist or reject other `owlbear_knowledge.*` imports outside that list, so the no-other-knowledge-imports contract can regress without failing. | Current imports are at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:9-17`. Test only checks hard-coded patterns at `tests/test_fetcher_protocol_1885.py:154-170`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC1-AC3 assertions to prove `FetchedDocument`, `FetchError`, and `FetchResult` are `BoundaryModel` subclasses, not just happy-path containers with matching fields/defaults. | `tests/test_fetcher_protocol_1885.py` | Review finding #1 |
| 2 | test-writer | Replace the AC4 protocol proof with assertions that inspect the declared `fetch_source` coroutine signature/annotations and fail on contract drift, rather than relying only on runtime `isinstance` protocol satisfaction. | `tests/test_fetcher_protocol_1885.py` | Review finding #2 |
| 3 | test-writer | Assert the AC5 docstring semantics explicitly, not just the presence of section headings. | `tests/test_fetcher_protocol_1885.py` | Review finding #3 |
| 4 | test-writer | Harden AC7 import-boundary coverage to validate the full allowed import set or parsed import graph, so any other `owlbear_knowledge.*` import fails the test. | `tests/test_fetcher_protocol_1885.py` | Review finding #4 |

## Observations
- This reject is about proof quality, not the current implementation: `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` presently matches the written AC on direct inspection.
- AC6 appears adequately implemented in `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py:51-55`, `:138`, `:191-195`, `:222`; no blocking issue found there.

[[2026-05-26T08:31:52+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_fetcher_protocol_1885.py`
**Proof bundle:** smoke (retry — strengthened assertions)

**Retry-cycle gap-fill (4 reviewer findings addressed):**

| Finding | Gap | New Test Added |
|---------|-----|----------------|
| AC1-AC3 | No BoundaryModel inheritance proof | `test_fetched_document_is_boundary_model_subclass`, `test_fetch_error_is_boundary_model_subclass`, `test_fetch_result_is_boundary_model_subclass` |
| AC4 | isinstance only; no signature/annotation contract | `test_source_fetcher_fetch_source_signature` — inspects async, source/cancel params, keyword-only, return annotation |
| AC5 | Heading presence only; no semantic content | `test_fetch_source_docstring_semantics` — asserts partial/cancel, errors/never, order, batch, transport, Raises-Never |
| AC7 | Hard-coded forbidden list; no allowlist enforcement | `test_fetcher_module_imports_only_from_allowlist` — AST-parses source, rejects any owlbear_knowledge.* outside explicit allowlist |

**Test totals:** 13 tests total (7 original + 6 new), all PASS
**Fail confirmation:** N/A — test-only retry; implementation correct; direct-to-review advance
**Lint:** ruff exit 0, clean

**AC coverage table (strengthened):**
| AC | Tests | Proof |
|----|-------|-------|
| AC1 FetchedDocument | 2 | field values + BoundaryModel subclass |
| AC2 FetchError | 2 | field values + BoundaryModel subclass |
| AC3 FetchResult | 2 | tuple defaults + BoundaryModel subclass |
| AC4 SourceFetcher | 2 | isinstance + signature/annotations/async |
| AC5 docstring | 2 | sections + semantic content |
| AC6 __init__ re-export | 1 | namespace + __all__ |
| AC7 import boundary | 2 | forbidden list + full AST allowlist |

[[2026-05-26T09:09:49+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1885 -> backlog | This is the second review cycle, and the strengthened tests still leave AC-level regressions undetectable for AC1-AC5 and AC7.
- Builder evidence reviewed first: the original builder note includes a clean scoped quality-runner run (7 passed, lint clean, 100% coverage for `owlbear_knowledge.protocols.fetcher`), and the retrying test-writer note reports 13 passing tests with clean lint.
- Direct code inspection still shows the implementation itself matches the written contract in `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` and the re-export surface in `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py`; the blocker remains proof quality.
- Focused file diagnostics are clean for `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py`, `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py`, and `tests/test_fetcher_protocol_1885.py`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1-AC3 | The strengthened model tests still do not prove the exact field contract. They cover happy-path construction plus `BoundaryModel` inheritance, but they never assert that `title`, `text`, `uri`, `uri/error` remain required, and they never assert that `FetchResult.documents/errors` keep the exact tuple element annotations required by the AC. Those parts of the contract can regress while the suite stays green. | Contract shape is declared at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:20`, `:30`, `:37`; current proof is limited to `tests/test_fetcher_protocol_1885.py:59`, `:68`, `:83`, `:89`, `:104`, `:110`. | backlog |
| 2 | AC4 | The signature test is still too loose to lock the protocol declaration. It proves coroutine status, parameter presence, `cancel` keyword-only/default semantics, and a substring match on the return annotation, but it does not prove the exact `source` parameter kind or the exact `FetchResult` return contract. A drift such as keyword-only `source` or `FetchResult | None` can still satisfy the current assertions. | Required signature is at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:48`; current assertions are at `tests/test_fetcher_protocol_1885.py:139`, `:144`, `:149`, `:158`, `:168`. | backlog |
| 3 | AC5 | The docstring test still matches isolated keywords rather than the full required clauses. It does not bind `partial documents on cancel`, `per-item failures in errors tuple, never raised`, `ordering`, `batch strategy`, `transport I/O`, and `Raises: never` tightly enough to fail on materially incorrect wording that still contains the same tokens. | Required semantics are documented at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:56`, `:61`, `:65`, `:68`; current proof is `tests/test_fetcher_protocol_1885.py:187`, `:193`, `:201`, `:214`. | backlog |
| 4 | AC7 | The allowlist test only constrains imports whose module path contains `owlbear_knowledge`. It still does not reject other non-stdlib, non-pydantic imports, so a forbidden third-party import could be added without failing the suite. | Actual imports are at `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py:9`, `:11`, `:13`, `:16`, `:17`; current allowlist logic is `tests/test_fetcher_protocol_1885.py:276`, `:284`, `:293`, `:300`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add AC1-AC3 assertions that fail when required fields gain defaults or when `FetchResult.documents/errors` drift away from the exact tuple element types required by the contract. | `tests/test_fetcher_protocol_1885.py` | Review finding #1 |
| 2 | test-writer | Tighten the AC4 protocol test to assert the exact declared signature, including the `source` parameter kind and an exact `FetchResult` return annotation. | `tests/test_fetcher_protocol_1885.py` | Review finding #2 |
| 3 | test-writer | Replace the AC5 keyword checks with clause-level assertions that prove each required guarantee, non-guarantee, side effect, and `Raises: never` statement. | `tests/test_fetcher_protocol_1885.py` | Review finding #3 |
| 4 | test-writer | Extend the AC7 import-boundary proof to fail on any non-stdlib, non-pydantic import outside the explicit knowledge allowlist, not only additional `owlbear_knowledge.*` imports. | `tests/test_fetcher_protocol_1885.py` | Review finding #4 |

## Observations
- AC6 remains adequately covered: the grouped re-export exists in `serve/knowledge/src/owlbear_knowledge/protocols/__init__.py:51`, and all four public names are present in `__all__` at `:191`, `:192`, `:195`, `:222`.
- This rejection is still about test quality rather than implementation correctness; no implementation defect was identified in the current fetcher module.

[[2026-05-26T10:15:00+02:00]]
## Architecture Review (Cycle 2)

### Context
Task has bounced twice from review. Implementation is correct (confirmed both cycles). All 13 tests pass at 100% coverage. The blocker is a proof-quality cycle: reviewer demands increasingly rigid type-contract assertions beyond what `smoke` bundle warrants.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged — pure protocol/model file |
| Interface clarity | PASS | AC already precise from first review |
| Dependency correctness | PASS | No changes needed |
| Module layering | PASS | Unchanged |
| TDD compliance | PASS | Tests exist and pass |
| KISS/YAGNI | PASS | No speculative additions |
| Premise challenge | PASS | Implementation committed, downstream #1886 depends on it |
| Pattern consistency | PASS | Matches existing protocol modules |
| Security surface | PASS | Internal protocol, no boundaries |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
N/A — pure type/protocol definition, no runtime logic.

### Design Diverge
Skipped — implementation complete, no alternative approaches to evaluate.

### Challenge Results
Skipped — second-cycle review-rejection triage, not a fresh approval. Original challenger findings already addressed in cycle 1.

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED (targeted additions only)

### Reviewer Findings Triage
The reviewer's findings fall into two categories:

**Accept (3 targeted additions):**
1. AC1-AC3: Add `assert FetchedDocument.model_fields['title'].is_required()` (and similarly for text, uri on each model) — proves fields remain required. 3 assertions total, one per model class.
2. AC4: Add `assert params['source'].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD` — locks source param kind against drift to keyword-only.
3. AC7: Extend allowlist test to also reject non-stdlib, non-pydantic, non-owlbear_knowledge top-level imports (add stdlib + pydantic to the allowed set in the AST walk).

**Decline (over-scope for smoke):**
- AC5 docstring clause-level assertions: Current semantic keyword checks are sufficient for smoke. Requiring exact prose matching makes tests brittle to editorial improvements and tests the documentation tool (docstrings), not the interface contract. The docstring is committed and correct.
- AC4 exact return type check: The test already asserts `FetchResult` in the return annotation string. Requiring exact identity match (`is FetchResult`) on a string-annotation module adds no real regression protection beyond what exists.

### Guidance for Test-Writer
Add ONLY these targeted assertions to break the review cycle:
1. In each AC1-AC3 test class, add one assertion per required field using `Model.model_fields[field_name].is_required()`
2. In the AC4 signature test, add `assert params['source'].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD`
3. In the AC7 allowlist test, build a complete allowed-module set (stdlib modules used + pydantic + the 3 knowledge modules) and reject ANY `import` or `from X import` where X is not in that set

Do NOT add clause-level docstring matching (AC5) or tighter return-type assertions (AC4 return). The reviewer's findings on those points exceed smoke scope.

### Verdict: APPROVE
### Action Taken: Resolved review-cycle deadlock by triaging reviewer findings into accept (3 targeted additions) vs decline (over-scope). Added explicit test-writer guidance for bounded scope. Proof bundle remains smoke. Advanced to todo.

[[2026-05-26T09:25:43+02:00]]
Architecture Review (Cycle 2): Resolved review-cycle deadlock. Triaged reviewer findings — accepted 3 targeted test additions (model field required-ness, param kind lock, full import allowlist) and declined 2 over-scope demands (clause-level docstring matching, exact return type identity). Added explicit test-writer guidance for bounded scope. Proof bundle remains smoke.
