---
id: 751
title: Authenticated Content Pipeline
status: archived
priority: medium
created: '2026-04-10T10:46:49.305763+00:00'
updated: '2026-04-14T07:04:36.576097+00:00'
tags:
- feature
- knowledge
- browser
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
# Authenticated Content Pipeline

## Investment Tier: Production

## Problem

OwlBear agents lack access to corporate knowledge that spans authenticated intranet sources. When agents perform knowledge-intensive work (security concepts, architecture docs, implementation planning), they can't reference corporate security requirements, solution blueprints, operating procedures, or tool documentation — because that content lives behind SSO on SharePoint, Confluence, internal web tools, and GitHub repos, and no pipeline exists to bring it into the knowledge graph.

The existing ingestion pipeline works for unauthenticated content. The gap is authenticated content: extraction through authenticated sessions, discovery of subpages from user-provided roots, user review of value, and ingestion with cross-source entity interconnection.

## Outcomes

1. Authenticated web content can be extracted programmatically via Edge CDP
2. A source management agent interactively onboards new sources
3. Ingested corporate content is queryable by pipeline agents with source attribution
4. Cross-source concepts are linked in the knowledge graph
5. Content freshness maintained through user-triggered refresh with replace-on-change semantics
6. Source removal cascade-deletes all associated content

## Approach

- Separate browser package (serve/browser/ + serve/mcp-browser/)
- Protocol injection (ContentFetcher) into knowledge pipeline
- AUTHENTICATED_WEB source type
- HTML→markdown cleaner + hash on cleaned content (ships with browser, not after)
- source_pages lifecycle table + source_id FK on documents
- Corporate entity types (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD)
- Full browser tool set with URL domain allowlist at tool level
- IDPI + untrusted content wrapping before go-live

## Delivery Phases

- Phase 0: Technical spike — validate Edge CDP on corporate laptop (go/no-go gate)
- Phase 1: Browser package + pipeline quality + schema + entity types + basic extraction
- Phase 2: Source management agent + interactive discovery + page review UX
- Phase 3: InterDocGraphBuilder for corporate types + cross-source linking
- Phase 4 (optional): SharePoint REST API parallel path

## Brief

Full brief: .owlbear/briefs/draft-browser-knowledge-extraction/brief.md

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/751-authenticated-content-pipeline.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Proceed with brief's approach as-is. Use trafilatura for HTML cleaning in Phase 1. Add trafilatura extraction quality test to Phase 0 spike alongside CDP validation. (confidence: .82)
- Follow-up tasks created: #774 (Phase 0: Edge CDP Technical Spike), #775 (Phase 1: Browser Package + Pipeline Quality + Schema — needs decomposition)
- Decision requests: T3 feature — blocking DR needed after Phase 0 spike completes (go/no-go gate)
- Challenge: FALLBACK — challenger subagent not available

### Key Findings
1. Playwright `connect_over_cdp` confirmed viable for Edge CDP (stable since v1.9, `is_local=True` since v1.58)
2. HTML cleaning comparison: trafilatura (.75 confidence) > readability-lxml + markdownify > markdownify + custom strip. html2text excluded (GPL-3.0)
3. Architecture fit validated: protocol injection, SourceType enum extension, lazy browser import all align with existing DI patterns
4. Content safety gap confirmed: ingest.py wrapping predicate must be inverted (wrap all except file/text)
5. Phased delivery (0→4) validated — dependency chain is correct

### Correction
Task #775 has `depends_on: [752]` which should be `depends_on: [774]` (Phase 0 task). Manual correction needed.
[[2026-04-10]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tracking epic for authenticated content pipeline feature. Children (#774, #775) carry single-responsibility implementation. |
| Interface clarity | PASS | Outcomes 1-6 map cleanly to delivery phases. Children have concrete AC. |
| Dependency correctness | PASS/FLAG | #751 itself has no deps (correct). **#775 has `depends_on: [752]` — must be corrected to `[774]`** (Phase 0 spike). Researcher noted this; manual correction still pending. |
| Module layering | PASS | Separate `serve/browser/` + `serve/mcp-browser/` packages respect layering. Protocol injection (`ContentFetcher`) into knowledge pipeline avoids upward imports. Package boundary test needs `owlbear_browser` and `owlbear_mcp_browser` entries. |
| TDD compliance | PASS | Children will go through RED/GREEN phases. #775 explicitly marked "Needs decomposition" for planner to create TDD task pairs. |
| KISS/YAGNI | PASS | Phase-gated delivery (0→4) with go/no-go gate prevents over-investment. Phase 4 (SharePoint REST) explicitly optional. |
| Premise challenge | PASS | No existing capability for authenticated content extraction. Existing pipeline handles only unauthenticated sources (URL_LIST, FILE_GLOB). Gap is real. |
| Pattern consistency | PASS | SourceType enum extension, RefreshOrchestrator handler dispatch, DI protocol injection, schema migration chain (v8→v9), entity/relation type extension — all follow established codebase patterns. |
| Security surface | PASS | Explicit security measures in approach: URL domain allowlist at tool level, IDPI + untrusted content wrapping, CDP binding to 127.0.0.1 only, content safety predicate inversion (wrap all except file/text). |
| Single domain | PASS | Multi-domain components (browser, knowledge, schema, MCP) are correctly decomposed into separate children. Epic tracks the overall feature. |

### Failure Mode Map

Not applicable — #751 is a tracking epic. Failure modes will be evaluated on implementation children.

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge; high confidence based on codebase evidence

### Codebase Evidence
- `SourceType` enum: `serve/knowledge/src/owlbear_knowledge/models.py:37-42` — extendable with AUTHENTICATED_WEB
- Content safety predicate: `serve/knowledge/src/owlbear_knowledge/ingest.py:191-196` — `_is_url = _meta.get("source_type") == "url"` confirms research finding of needed inversion
- RefreshOrchestrator: `serve/knowledge/src/owlbear_knowledge/refresh.py:86-93` — handler dispatch pattern ready for new source type
- Schema: `serve/knowledge/src/owlbear_knowledge/schema.py:19` — currently v8, v9 migration is natural next step
- Package boundaries: `tests/test_package_boundary.py:43-50` — ALLOWED_IMPORTS needs `owlbear_browser` and `owlbear_mcp_browser` entries

### Action Items
1. **#775 dependency fix**: `depends_on` must be corrected from `[752]` to `[774]` — orchestrator or next agent touching #775 should fix this
2. **Pass-through tag**: Added `quality` tag since #751 is a non-implementation tracking epic

### Verdict: APPROVE
### Action Taken: Advanced #751 to todo. Flagged #775 dependency correction (752→774) for orchestrator action.
[[2026-04-10]]
## Test-Writer Notes

**Test file:** `tests/test_authenticated_content_pipeline_751.py`

**Classes:**
| Class | AC | Tests | Category breakdown |
|---|---|---|---|
| `TestFromAC_AuthenticatedContentModels` | AC1-3 | 11 | 9 happy, 1 boundary, 1 edge |
| `TestFromAC_AuthenticatedContentProtocol` | AC4 | 4 | 3 happy, 1 boundary |
| `TestFromAC_AuthenticatedContentSafety` | AC5 | 3 | 2 happy, 1 boundary |
| `TestFromAC_AuthenticatedContentSchema` | AC6 | 8 | 5 happy, 1 boundary, 1 edge, 1 migration |
| `TestFromAC_AuthenticatedContentExtractionPrompt` | AC7 | 6 | 6 happy |
| `TestFromAC_AuthenticatedContentPackageBoundaries` | AC8 | 5 | 3 happy, 1 boundary, 1 error |

**Total: 37 tests, all FAIL — confirmed by pytest run (37 failed, 0 passed)**

**AC Coverage:**
| AC | Description | Tests |
|---|---|---|
| AC1 | SourceType.AUTHENTICATED_WEB enum value | 3 |
| AC2 | Corporate EntityTypes (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD) | 6 |
| AC3 | Corporate RelationTypes (GOVERNS, SUPERSEDES_VERSION) | 2 |
| AC4 | ContentFetcher protocol in owlbear_knowledge.protocol | 4 |
| AC5 | IngestPipeline wraps authenticated_web chunks | 3 |
| AC6 | Schema v9: source_pages table + source_id on documents | 8 |
| AC7 | LLM_EXTRACTION_PROMPT includes corporate entity/relation types | 6 |
| AC8 | ALLOWED_IMPORTS: owlbear_browser + owlbear_mcp_browser | 5 |

**Failure reasons by class:**
- Models: `AttributeError`/`AssertionError` — enum members absent
- Protocol: `ImportError` — ContentFetcher not in owlbear_knowledge.protocol
- Safety: `AssertionError` — predicate only checks "url", not "authenticated_web"
- Schema: `AssertionError` — _SCHEMA_VERSION is 8, source_pages absent, documents.source_id absent
- Prompt: `AssertionError` — corporate keywords absent from LLM_EXTRACTION_PROMPT
- Boundaries: `AssertionError`/`ModuleNotFoundError` — owlbear_browser namespace not in ALLOWED_IMPORTS, package not installed

**Ruff:** clean
[[2026-04-10]]
## Builder Notes

**Verdict:** DONE → review

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/models.py` — Added `SourceType.AUTHENTICATED_WEB`, `EntityType.{REQUIREMENT,SOLUTION,PROCEDURE,POLICY,STANDARD}`, `RelationType.{GOVERNS,SUPERSEDES_VERSION}`
- `serve/knowledge/src/owlbear_knowledge/protocol.py` — Added `@runtime_checkable ContentFetcher` protocol with `async fetch(url: str) -> str`
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — Fixed content-wrapping predicate: `_is_url` now matches `{"url","authenticated_web"}`
- `serve/knowledge/src/owlbear_knowledge/schema.py` — Bumped `_SCHEMA_VERSION` to 9; added `_CREATE_SOURCE_PAGES` DDL; added `source_id` to `_CREATE_DOCUMENTS`; added `_migrate_v8_to_v9` (creates `source_pages`, adds `documents.source_id`); extracted `_apply_migrations()` helper to keep `init_db` complexity ≤ C901 limit
- `tests/test_package_boundary.py` — Added `owlbear_browser: set()` and `owlbear_mcp_browser: {"owlbear_browser"}` to `ALLOWED_IMPORTS`
- `serve/browser/` (NEW) — Minimal `owlbear-browser` workspace package
- `serve/mcp-browser/` (NEW) — Minimal `owlbear-mcp-browser` workspace package (required by manifest guard test)

### Test Results
- **37 passed, 0 failed** — all `TestFromAC_*` classes in `test_authenticated_content_pipeline_751.py`
- Pre-existing failure: `test_package_boundary.py::TestFromAC_ManifestGuard::test_allowed_imports_keys_match_discovered_namespaces` (fails on `owlbear_voice` which has no directory — pre-dates this task, unrelated to #751)

### Coverage (target modules)
- `models.py`: 99%
- `protocol.py`: 100%
- `ingest.py`: 65% (full module; AC-specific paths covered)
- `schema.py`: 64% (full module; migration paths covered by full suite)

### Lint
- `ruff check` — **All checks passed**

### Commit
`2dfae28b` — feat: authenticated content pipeline Phase 1 — models, protocol, schema, safety (#751, builder)
[[2026-04-10]]
## Review Evidence

### Test Results
- pytest: 38 passed, 1 failed
- Failed: `tests/test_package_boundary.py::TestFromAC_ManifestGuard::test_allowed_imports_keys_match_discovered_namespaces` — pre-existing failure on `owlbear_voice` (not present under `serve/*/src/`). Not introduced by this builder. Builder noted it explicitly. Confirmed by code-reader.
- All 37 tests in `tests/test_authenticated_content_pipeline_751.py`: PASS

### Lint
clean: true

### Coverage
- `owlbear_knowledge.models`: 99%
- `owlbear_knowledge.protocol`: 100%
- `owlbear_knowledge.ingest`: 65% (full module; AC-specific paths covered per builder note)
- `owlbear_knowledge.schema`: 64% (full module; migration paths confirmed by AC6 tests)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 SourceType.AUTHENTICATED_WEB | `test_source_type_authenticated_web_exists/value/member` (3) | Yes — hasattr + value + membership | COVERED |
| AC2 EntityType × 5 | `test_entity_type_{x}_exists` × 5 + collision guard | Yes — direct hasattr checks | COVERED |
| AC3 RelationType GOVERNS/SUPERSEDES_VERSION | `test_relation_type_governs_exists` + `test_relation_type_supersedes_version_exists` | Yes — hasattr | COVERED |
| AC4 ContentFetcher protocol | 4 tests — import, subclass check, has fetch, params | Yes — direct assertion | COVERED |
| AC5 authenticated_web wrapping | 3 tests (all use `source_type="authenticated_web"`) | Partial — `"url"` path not tested | **LAX** |
| AC6 schema v9 | 8 tests — version, table, columns, v8→v9 migration | Yes — schema introspection | COVERED |
| AC7 prompt includes corporate types | 6 tests — requirement, solution, procedure, policy, standard, governs | **MISSING supersedes_version** — no test, no compensating TestBuilderDiscovered | **LAX / no compensation → FAIL** |
| AC8 ALLOWED_IMPORTS | 4 structural + 1 importability test | Yes — direct dict lookup + import | COVERED |

**Findings:** 1 LAX (AC5) + 1 LAX-no-compensation (AC7 SUPERSEDES_VERSION) → FAIL

#### Security Review
- No OWASP Top 10 critical issues in builder's changed files.
- `content_safety.py:32`: unescaped `source_url` in sentinel tag attribute (INFORMATIONAL — file is NOT in builder's changed file list; pre-existing issue). Reported to inform future fix.
- `ingest.py:182`: trust assumption on caller-supplied `source_type` metadata documented correctly for internal-only use. Acceptable.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ManifestGuard` (test_package_boundary.py) | Added `owlbear_browser: set()` and `owlbear_mcp_browser: {"owlbear_browser"}` to `ALLOWED_IMPORTS` | PRESERVED — directories exist, tests pass for new entries |
| `TestFromAC_PackageBoundaries` | No modification | PRESERVED |
All `TestFromAC_*` classes in `test_authenticated_content_pipeline_751.py`: no modifications by builder. PRESERVED.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC5 uses `len(calls) >= 1`; `== 1` would be stronger but single-chunk setup makes this not WEAK |
| Negative/error-path coverage | WEAK — AC5 ONLY | No test for `source_type=None` or `source_type="file_glob"` NOT being wrapped |
| Manual mutation resistance | WEAK — AC5 ONLY | Remove `"url"` from predicate set, all 3 AC5 tests still pass |
| Test independence | No shared mutable state observed | ADEQUATE |
| Descriptive names | Yes — all `TestFromAC_*` with descriptive method names | ADEQUATE |

Note: WEAK ratings are scoped to AC5 only and overlap with the 5.5 gap below.

#### Data Safety
- `ContentFetcher.fetch` returns unbounded `str` with no documented size limit — informational risk for large intranet pages flowing through chunking + LLM extraction. No validation layer. (INFORMATIONAL — protocol only, no concrete impl in scope)
- `except Exception` swallow at `ingest.py:197` is pre-existing; authenticated_web adds new failure modes that will surface silently. (INFORMATIONAL — not introduced by this builder)

#### Implementation-Aware Gaps — **FAIL**
1. **AC5 regression path** (`ingest.py:182`): predicate changed from `== "url"` to `in {"url", "authenticated_web"}`. All 3 AC5 tests use `source_type="authenticated_web"` only. If `"url"` were removed from the set, original URL_LIST wrapping silently breaks with 0 test failures. Significant — `URL_LIST` sources are production behavior.
2. **AC5 negative path**: No test for `source_type=None` / `source_type="file_glob"` verifying content is NOT wrapped. Predicate broadening with no boundary test.
3. **AC7 supersedes_version prompt test** (`llm_extractor.py:30`): f-string builds prompt from enum values. `TestFromAC_AuthenticatedContentExtractionPrompt` skips `supersedes_version`. If `SUPERSEDES_VERSION` were removed from `RelationType`, 0 prompt tests catch it.
4. **AC4 `isinstance` duck-typing** (`protocol.py`, `test_authenticated_content_pipeline_751.py:122`): `issubclass(ContentFetcher, Protocol)` only — does not verify `isinstance(stub_with_fetch, ContentFetcher)` returns `True`. `@runtime_checkable` behaviour is the primary consumer use case and remains untested.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `ingest.py:182`: variable named `_is_url` now covers two source types; `_needs_wrapping` would reduce confusion as the set grows (6.1)
- `ingest.py` docstring reads `source_type == "url"` but code checks set membership (6.2)
- `TestFromAC_AuthenticatedContentExtractionPrompt`: 6 structurally identical tests; `@pytest.mark.parametrize` would reduce duplication without losing coverage (6.3)
- `content_safety.py:32`: `source_url` not quote-escaped in sentinel tag attribute — pre-existing, not in builder's changed files (6.1 security informational)

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 SourceType.AUTHENTICATED_WEB | `models.py` — AUTHENTICATED_WEB value "authenticated_web" | `test_source_type_authenticated_web_*` (3) | PASS |
| AC2 EntityType corporate × 5 | `models.py` — five new EntityType members | `test_entity_type_{x}_exists` × 5 | PASS |
| AC3 RelationType GOVERNS + SUPERSEDES_VERSION | `models.py` — two new RelationType members | `test_relation_type_governs/supersedes_version_exists` | PASS |
| AC4 ContentFetcher protocol | `protocol.py` — @runtime_checkable ContentFetcher, async fetch(url:str)->str | 4 tests | PASS |
| AC5 wrapping authenticated_web | `ingest.py:182` — predicate covers `{"url","authenticated_web"}` | 3 tests (authenticated_web only; url path uncovered) | **PARTIAL** |
| AC6 schema v9 | `schema.py` — _SCHEMA_VERSION=9, source_pages DDL, source_id on documents, _migrate_v8_to_v9 | 8 tests | PASS |
| AC7 prompt includes corporate types | `llm_extractor.py` — f-string with EntityType/RelationType values | 6 tests (supersedes_version missing) | **PARTIAL** |
| AC8 ALLOWED_IMPORTS browser entries | `test_package_boundary.py` — owlbear_browser + owlbear_mcp_browser added | 5 tests in 751 test file | PASS |

### Confidence: .87
### Verdict: FAIL

**Routing: todo** — test-writer adds missing coverage:
1. AC5 regression: `source_type="url"` still wraps after predicate change (tests/test_authenticated_content_pipeline_751.py)
2. AC5 negative path: `source_type="file_glob"` / `None` does NOT wrap
3. AC7: `supersedes_version` keyword appears in `LLM_EXTRACTION_PROMPT`
4. AC4 (optional/low): `isinstance(stub_with_fetch, ContentFetcher)` returns `True` for duck-typed objects

[[2026-04-10]]
## Test-Writer Notes

**Retry:** Added 5 tests addressing all 4 reviewer-flagged gaps.

**New tests added to `tests/test_authenticated_content_pipeline_751.py`:**

| Class | New Test | Gap Addressed | Result |
|---|---|---|---|
| `TestFromAC_AuthenticatedContentProtocol` | `test_content_fetcher_isinstance_duck_typing` | AC4 `@runtime_checkable` isinstance | PASS — implementation correct |
| `TestFromAC_AuthenticatedContentSafety` | `test_url_sourced_ingest_wraps_chunk` | AC5 regression: `"url"` still wraps | PASS — predicate set intact |
| `TestFromAC_AuthenticatedContentSafety` | `test_file_glob_sourced_ingest_does_not_wrap_chunk` | AC5 negative: `"file_glob"` not wrapped | PASS — predicate correct |
| `TestFromAC_AuthenticatedContentSafety` | `test_none_source_type_does_not_wrap_chunk` | AC5 boundary: absent `source_type` not wrapped | PASS — predicate correct |
| `TestFromAC_AuthenticatedContentExtractionPrompt` | `test_extraction_prompt_includes_supersedes_version_relation_type` | AC7 `supersedes_version` in prompt | PASS — f-string includes RelationType values |

**pytest result:** 42 tests collected — 40 passed, 2 failed
- 5 new tests: all PASS (implementation already correct — builder's `2dfae28b` covered these)
- 37 existing tests: 35 PASS, 2 FAIL (pre-existing — schema uses `status` column not `approval_state`; `extraction_status` column absent; NOT introduced by this retry)

**Pre-existing failures (out of retry scope — builder to address in next GREEN phase):**
- `test_source_pages_has_approval_state_column` — schema has `status DEFAULT 'discovered'`, not `approval_state`
- `test_source_pages_has_extraction_status_column` — column absent from source_pages DDL

**ruff:** clean
**Commit:** `db9a6059` — test: add retry coverage for AC5 regression/negative paths, AC7 supersedes_version, AC4 isinstance (#751, test-writer)
[[2026-04-10]]
## Builder Notes

**Verdict:** DONE → review

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/schema.py` — Renamed `status TEXT DEFAULT 'discovered'` to `approval_state TEXT DEFAULT 'discovered'` and added `extraction_status TEXT DEFAULT 'pending'` to `_CREATE_SOURCE_PAGES` DDL. The original builder had used a generic `status` column where the AC required `approval_state` and a separate `extraction_status` column.

### Root Cause
Test-writer retry notes identified two pre-existing failures from the original builder commit (`2dfae28b`):
- `test_source_pages_has_approval_state_column` — schema had `status`, not `approval_state`
- `test_source_pages_has_extraction_status_column` — `extraction_status` column was absent entirely

### Test Results
- **42 passed, 0 failed** — all `TestFromAC_*` classes in `test_authenticated_content_pipeline_751.py`
- No builder-discovered tests (fix was a pure DDL alignment to AC, no logic edge cases)

### Coverage
- Target module `schema.py`: DDL-level change only; schema introspection tests cover the new columns via `PRAGMA table_info(source_pages)`

### Lint
- `ruff check serve/knowledge/src/owlbear_knowledge/schema.py` — **All checks passed**

### Commit
`be9610a3` — fix: add approval_state + extraction_status columns to source_pages DDL (#751, builder)
[[2026-04-10]]
## Review Evidence

### Test Results
- quality-runner: **FATAL — pytest KeyboardInterrupt during startup on Windows**. Tried 2 retries + plugin-disabled invocation + subprocess fallback. All failed. Independent test execution not possible in this review cycle.
- Prior independent test run (Review Pass 1, same task): 38 passed, 1 failed (pre-existing `owlbear_voice` boundary failure).
- Test-writer retry self-report: 42 collected, 40 passed, 2 failed (schema column failures — fixed by builder 2).
- Builder 2 self-report: 42 passed, 0 failed.
- **Cannot independently verify current state. Block required per skill.**

### Lint
Not executed (Quality-Runner unavailable). Builder and test-writer both report ruff clean. Prior review confirmed clean.

### Coverage
Not executed this cycle. Prior review: models 99%, protocol 100%, ingest 65%, schema 64%.

### Schema Fix Verification (independent, via file read)
- `schema.py:19` — `_SCHEMA_VERSION: int = 9` ✓
- `schema.py:157` — `approval_state TEXT DEFAULT 'discovered'` ✓
- `schema.py:158` — `extraction_status TEXT DEFAULT 'pending'` ✓
- `schema.py:252–254` — `_migrate_v8_to_v9` creates source_pages and index ✓

### Code-Reader Report — AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 SourceType.AUTHENTICATED_WEB | `models.py` — AUTHENTICATED_WEB = "authenticated_web" | `test_source_type_*` × 3 | PASS |
| AC2 EntityType corporate × 5 | `models.py` — 5 new members | `test_entity_type_{x}_exists` × 5 + collision guard | PASS |
| AC3 RelationType GOVERNS + SUPERSEDES_VERSION | `models.py` — 2 new members | `test_relation_type_*` × 2 (hasattr — compensated by AC7 prompt tests) | PASS |
| AC4 ContentFetcher @runtime_checkable | `protocol.py` — async fetch(url:str)->str | 5 tests incl. isinstance duck-typing | PASS |
| AC5 wrapping url + authenticated_web | `ingest.py` — predicate set `{"url","authenticated_web"}` | 4 tests: +/- for each source type | PASS |
| AC6 schema v9 | `schema.py:19,152–158,252–254` — version, DDL, migration | 8 tests + column existence confirmed | PASS |
| AC7 prompt includes corporate types incl. supersedes_version | `llm_extractor.py` — dynamic enum join | 7 tests: 6 entity/relation + supersedes_version | PASS |
| AC8 ALLOWED_IMPORTS browser entries | `test_package_boundary.py` — both entries added | 5 tests | PASS |

### Test Integrity
All `TestFromAC_*` classes intact — no weakening or removal by builder or test-writer. 5 retry tests (test-writer) confirmed genuine and mutation-resistant by code-reader.

### Pass 1 — CRITICAL Findings (Code-Reader Evidence)
None that change the verdict. Pre-existing `source_url` unescaped in `content_safety.py:38` is not in builder's changed files (carried from prior review INFORMATIONAL note).

### Pass 2 — INFORMATIONAL
- `ingest.py:182`: `_is_url` variable name misleading post-expansion; `_needs_wrapping` preferred (6.1)
- AC6 DEFAULT values (`'discovered'`, `'pending'`) not asserted by schema tests — AC6 text says "source_id on documents" not "default values required" so this is advisory (6.3)
- AC3 value assertions absent but compensated by AC7 prompt tests which are mutation-resistant (6.3)
- `source_pages.source_id` and `documents.source_id` have no REFERENCES clause — Approach mentioned "FK" but formal AC6 does not; no FK test required (6.1 informational)
- `TestFromAC_AuthenticatedContentSafety`: mock scaffold repeated per test — `@pytest.fixture` would reduce 40 lines of duplication (6.3)

### Confidence
Unable to assign without independent test execution.

### Block Reason
Quality-Runner fatal (Windows pytest startup hang, 2 attempts). Skill requires independent test execution. Unblock: `uv run pytest tests/test_authenticated_content_pipeline_751.py -v` — confirm 42 passed, 0 failed, then re-queue to review.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: 41 passed, 0 failed (`test_authenticated_content_pipeline_751.py`). Unblocked for review continuation.

[[2026-04-14]]
## CDP Pivot Notice
CDP spike (#753) result: NO-GO — Group Policy `RemoteDebuggingAllowed=0` blocks all CDP on corporate laptop.

**Validated pivot:** Playwright Chromium + Microsoft SSO extension. E2E PoC results:
- SharePoint Online: 1.7 MB HTML → 5.8 KB markdown (fully automatic SSO)
- Jira (Skyway on-prem): 815 KB → 67 KB (one-time login, then session persists)
- Confluence (Skyway on-prem): automatic via shared Skyway session

**Impact on task tree:**
- Archived: #753, #760, #782, #787 (scope:browser CDP tasks), #853, #854, #859 (scope:mcp-browser CDP session tasks)
- Still valid: #836 (ctx:Context refactor — browser-agnostic), #852 (BrowserContentFetcher wiring — abstraction stays), #855 (Playwright version bump)
- New pivot tasks created below this parent

See `.owlbear/research/cdp-spike-results.md`.
[[2026-04-14]]
## Review Evidence

### Test Results (independent — Quality-Runner, 2026-04-14)
`tests/test_authenticated_content_pipeline_751.py`: **41 passed, 0 failed** (exit code 0)

First attempt fatal (WMI hang — recurring Windows issue). Second attempt with narrower scope succeeded cleanly.

### Lint
`ruff check` on builder's changed files: **clean**.
Only violation returned: `engine.py:472 E501` — **NOT in builder's changed file set** (unrelated `owlbear_kanban.engine`). Pre-existing.

### Coverage
| Module | % | Notes |
|--------|---|-------|
| `owlbear_knowledge.models` | 99 | All new enums covered |
| `owlbear_knowledge.protocol` | 100 | ContentFetcher fully covered |
| `owlbear_knowledge.content_safety` | 83 | AC5 deny-list paths covered |
| `owlbear_knowledge.ingest` | 62 | Full module; AC-specific predicate paths covered |
| `owlbear_knowledge.schema` | 64 | Full module; v9 migration paths covered |

---

### Step 1 — Source Control (builder commits in scope)
Commits: `2dfae28b` (builder 1), `be9610a3` (builder 2 schema fix), `db9a6059` (test-writer retry).
Changed files: `models.py`, `protocol.py`, `ingest.py`→`content_safety.py` (via #781), `schema.py`, `test_package_boundary.py`, `serve/browser/`, `serve/mcp-browser/`.

**Task #797 note:** Child task `1825ed4e` replaced two builder-added tests (`test_source_pages_has_approval_state_column`, `test_source_pages_has_extraction_status_column`) with `test_source_pages_has_status_column`, per architect-approved #754 design (unified `PageStatus` enum, deny `approval_state`/`extraction_status` builder additions). This was NOT a builder modification — it was an authorized downstream correction. Removed tests covered builder-added columns that were OUTSIDE the AC6 spec. AC6 coverage is maintained (7 tests, all passing).

---

### 5.0 AC Coverage Table

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: `SourceType.AUTHENTICATED_WEB` | `test_source_type_*` × 3 (hasattr, value, membership) | YES — AttributeError/AssertionError | COVERED |
| AC2: EntityType REQUIREMENT/SOLUTION/PROCEDURE/POLICY/STANDARD | `test_entity_type_{x}_exists` × 5 + collision guard | YES — KeyError per missing member | COVERED |
| AC3: RelationType GOVERNS + SUPERSEDES_VERSION | `test_relation_type_{governs,supersedes}_exists` × 2 | YES — hasattr + AC7 prompt guard | COVERED |
| AC4: `ContentFetcher` `@runtime_checkable` protocol | 5 tests (import, issubclass, fetch method, params, isinstance duck-typing) | YES — ImportError, assertion on runtime_checkable | COVERED |
| AC5: wrapping `url` + `authenticated_web`; NOT file_glob/None | 6 tests (3 original + 3 retry: +url regression, +file_glob boundary, +None boundary) | YES — wrapping/non-wrapping behavioral assertions | COVERED |
| AC6: schema v9, source_pages, source_id on documents | 7 tests (version=9, table exists, source_id/url/status columns, documents.source_id, v8→v9 migration) | YES — PRAGMA introspection + migration execution | COVERED |
| AC7: `LLM_EXTRACTION_PROMPT` includes corporate types incl. `supersedes_version` | 7 tests (6 types + 1 relation — `supersedes_version` added in retry) | YES — substring assertion on dynamic enum join | COVERED |
| AC8: `ALLOWED_IMPORTS` browser entries | 5 tests (owlbear_browser present, owlbear_mcp_browser present, layer rules, importability) | YES — dict lookup + import | COVERED |

No MISSING entries. No WEAK assertions detected.

---

### 5.1 Security Review
- `ingest.py` / `content_safety.py`: deny-list (`frozenset({"file","file_glob","text"})`) — defense-in-depth: all unknown future source types are wrapped by default ✓
- `schema.py` DDL uses string templates (no user input) ✓
- `protocol.py`: no I/O ✓
- No hardcoded secrets, path traversal, injection, or insecure deserialization ✓
- Pre-existing `except Exception` swallow at `ingest.py` — not introduced by this builder (INFORMATIONAL)

**No security issues.**

---

### 5.2 TestFromAC Integrity

| Test | Change | By Whom | Assessment |
|------|--------|---------|------------|
| `TestFromAC_AuthenticatedContentModels` (11) | None | — | PRESERVED |
| `TestFromAC_AuthenticatedContentProtocol` (5) | test_isinstance duck-typing added (retry) | test-writer retry | STRENGTHENED |
| `TestFromAC_AuthenticatedContentSafety` (6) | 3 tests added (url regression, file_glob boundary, None boundary) by retry | test-writer retry | STRENGTHENED |
| `TestFromAC_AuthenticatedContentSchema` (7) | approval_state + extraction_status tests REMOVED; status test ADDED | Task #797 (authorized) | CORRECTED — tests targeted builder-added columns outside AC6 spec |
| `TestFromAC_AuthenticatedContentExtractionPrompt` (7) | supersedes_version test ADDED (retry) | test-writer retry | STRENGTHENED |
| `TestFromAC_AuthenticatedContentPackageBoundaries` (5) | None | — | PRESERVED |

No WEAKENED or REMOVED tests by the #751 builder. Task #797 modification is an authorized architectural correction, not a builder integrity violation.

---

### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | hasattr + value equality + PRAGMA introspection + behavioral wrapping |
| Negative/error-path coverage | STRONG | file_glob NOT wrapped, None NOT wrapped, schema migration tested |
| Mutation resistance | STRONG | Remove enum member → KeyError; flip predicate → AssertionError; change DDL → PRAGMA fails |
| Test independence | STRONG | No shared mutable state; in-memory SQLite per test |
| Descriptive names | STRONG | All `TestFromAC_*` with descriptive method names |

No WEAK ratings.

---

### AC Compliance Table (runtime evidence)

| AC | Evidence | Test Result | Status |
|----|----------|-------------|--------|
| AC1 | `models.py:47` AUTHENTICATED_WEB = "authenticated_web" | 3/3 pass | PASS |
| AC2 | `models.py:17-27` 5 corporate EntityType members | 6/6 pass | PASS |
| AC3 | `models.py:31-39` GOVERNS + SUPERSEDES_VERSION | 2/2 pass | PASS |
| AC4 | `protocol.py:95-103` @runtime_checkable ContentFetcher, async fetch | 5/5 pass | PASS |
| AC5 | `content_safety.py:23-40` deny-list, url+authenticated_web wrapped | 6/6 pass | PASS |
| AC6 | `schema.py:18,154-165,149-157` v9, source_pages DDL, migration | 7/7 pass | PASS |
| AC7 | `llm_extractor.py:12-13` dynamic enum join covers all 7 types | 7/7 pass | PASS |
| AC8 | `test_package_boundary.py` owlbear_browser + owlbear_mcp_browser in ALLOWED_IMPORTS | 5/5 pass | PASS |

---

### Deductions
| Finding | Deduction |
|---------|-----------|
| First quality-runner attempt fatal (WMI hang) — environment issue, not code defect | −0.01 |
| ingest / schema module coverage below 90% (pre-existing code dilutes; AC paths confirmed covered) | −0.01 |

### Confidence: 0.98 → PASS
[[2026-04-14]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `.github/copilot-instructions.md` is 9 lines (identity + branches only) — no tables track source types, protocols, or packages. No actionable update. |
| 2 | Module docstrings | Yes | Verified | `models.py`: `EntityType`, `RelationType`, `SourceType` class docstrings present; new `PageStatus` + `SourcePage` have docstrings. `protocol.py`: `ContentFetcher` has class docstring. `schema.py`: module docstring lists `source_pages`; `_migrate_v8_to_v9`, `_apply_migrations`, `init_db` all have docstrings. `content_safety.py`: module + `should_wrap` + `wrap_untrusted_content` all have docstrings. `ingest.py`: module docstring accurate (predicate delegated to `content_safety` via #781 — stale-docstring informational from review is resolved). |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains a "Authenticated Content Pipeline (Task #751)" section with 4 rows (Playwright, trafilatura, markdownify, browser-use). Present and current. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/751-authenticated-content-pipeline.md` exists; linked from task body under "## Research". |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/751-*` files found)
[[2026-04-14]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 SourceType.AUTHENTICATED_WEB | models.py:47, 3 tests pass | PASS |
| AC2 EntityType corporate x5 | models.py:17-27, 6 tests pass | PASS |
| AC3 RelationType GOVERNS + SUPERSEDES_VERSION | models.py:31-39, 2 tests pass | PASS |
| AC4 ContentFetcher @runtime_checkable | protocol.py:97, 5 tests pass (incl. isinstance) | PASS |
| AC5 wrapping url + authenticated_web | content_safety.py deny-list inversion, 6 tests pass (incl. regression + negative) | PASS |
| AC6 schema v9 + source_pages + source_id | schema.py:18 v9, DDL confirmed, 7 tests pass | PASS |
| AC7 prompt includes corporate types | llm_extractor.py dynamic enum join, 7 tests pass (incl. supersedes_version) | PASS |
| AC8 ALLOWED_IMPORTS browser entries | test_package_boundary.py updated, 5 tests pass | PASS |

### Test Results
- pytest (task-scoped): 41 passed, 0 failed
- pytest (full suite): 4194 passed, 363 failed, 8 skipped -- zero failures in #751 scope; all 363 are pre-existing from unrelated tasks
- test_package_boundary ManifestGuard failure: pre-existing owlbear_voice issue, not #751
- ruff: clean (all deliverable files)

### Architect Quality: 4/5
AC was specific and testable across all 8 lines. Minor gap: source_pages column naming ambiguity (approval_state vs status) required one builder fix round. Pipeline self-corrected successfully.

### Deduction Breakdown
- No AC lines without evidence: -0.00
- No lint violations: -0.00
- AC quality 4 (above 3 threshold): -0.00
- Reviewer evidence present and detailed: -0.00
- No full-suite failures in task scope: -0.00

### Confidence: .98
### Action: archive

### Commits Verified
- 2dfae28b feat: authenticated content pipeline Phase 1 (builder)
- db9a6059 test: add retry coverage AC5/AC7/AC4 (test-writer)
- be9610a3 fix: approval_state + extraction_status columns (builder fix)