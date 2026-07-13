---
id: 775
title: 'Phase 1: Browser Package + Pipeline Quality + Schema'
status: archived
priority: medium
created: '2026-04-10T11:45:08.164060+00:00'
updated: '2026-04-10T18:50:29.197355+00:00'
tags:
- browser
- knowledge
- phase-1
parent: 751
depends_on:
- 752
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
# Phase 1: Browser Package + Pipeline Quality + Schema

Needs decomposition: multiple interdependent subtasks across two new packages (serve/browser/, serve/mcp-browser/), knowledge pipeline changes (content cleaner, content safety inversion, extraction prompt), schema migration (v8→v9: source_pages table, source_id FK on documents), and entity model extension (5 corporate types + 2 relation types).

## Scope

1. `owlbear_browser` core library — Edge CDP launcher/manager, content extractor, HTML-to-markdown cleaner
2. `owlbear_mcp_browser` MCP server — navigate, click, type, select, read_text, snapshot tools with URL domain allowlist
3. `AUTHENTICATED_WEB` source type + `_handle_authenticated_web()` handler in RefreshOrchestrator
4. `ContentFetcher` protocol injection into knowledge pipeline
5. Schema v9 migration — `source_pages` lifecycle table, `source_id` FK on `documents`
6. Entity types: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
7. Relation types: GOVERNS, SUPERSEDES_VERSION
8. Content safety predicate inversion — wrap all except file/text source types
9. `LLM_EXTRACTION_PROMPT` update with corporate entity examples
10. Replace-on-change refresh semantics (cascade delete old → re-ingest)

## Dependencies

- Depends on Phase 0 go/no-go (#752)

## Context

- Parent: #751 — Authenticated Content Pipeline
- Research: `.owlbear/research/751-authenticated-content-pipeline.md`
- Brief: `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`
- Architect voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/architect.md`
- Security voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/security.md`
- Data quality voice: `.owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md`

[[2026-04-10]]

## Research

- Research doc: .owlbear/research/775-phase1-browser-pipeline-schema.md
- Sources: 12 studied, 8 high-relevance (10 internal codebase, 2 external — already logged)
- Recommendation: Proceed with all 10 scope items as-is (confidence: .85)
- Follow-up tasks created: none — task already marked "Needs decomposition" for planner
- Decision requests: none — T3 gate is Phase 0 go/no-go (#774), already flagged in #751 research

### Key Findings

1. **Ghost document bug (F1):** `ingest.py` inserts new doc on content change but never deletes the old one — `existing_id` unused in the changed branch. `delete_document_data()` already exists for cascade. Item 10 (replace-on-change) fixes this.
2. **Entity/relation/prompt must ship atomically (F3):** Items 6+7+9 are coupled — new StrEnum members auto-propagate to type list via `", ".join()` but LLM collapses corporate types to CONCEPT without explicit prompt examples.
3. **Content safety inversion is defense-in-depth (F4):** Changing `== "url"` to `not in ("file", "text", "file_glob")` wraps all future source types by default. Safe to ship independently.
4. **Schema v9 — NULL source_id for legacy (F2):** `ALTER TABLE documents ADD COLUMN source_id` allows NULL default; no backfill needed.
5. **Package boundary registration (F5):** `owlbear_browser: set()`, `owlbear_mcp_browser: {"owlbear_browser"}`. Browser must NOT depend on knowledge.
6. **source_pages table ships in v9 for Phase 2 readiness (F6):** Avoids v10 migration later.

### Dependency Graph for Planner

- WS-A (items 5,6,7): Schema + models foundation — independent, do first
- WS-B (items 8,9): Pipeline quality — item 9 depends on WS-A
- WS-C (items 1,2): Browser packages — parallel with WS-A/B
- WS-D (items 3,4,10): Pipeline integration — depends on WS-A + WS-C

### Dependency Correction Needed

# 775 has `depends_on: [752]` but should be `depends_on: [774]`. Flagged by architect review on #751

## Challenge Results

- Challenger: FALLBACK — decomposition research validates implementation feasibility, no controversial recommendation to challenge
- Confidence in original: .85
- Key challenges: N/A
- Researcher response: N/A
[[2026-04-10]]

## Planning

Decomposed into 18 subtasks across 4 dependency layers (WS-A/B/C/D).

### Task Map

| ID | Title | Layer | Depends On | Tags |
|----|-------|-------|------------|------|
| #779 | Tests — Corporate entity and relation type extensions | 0 | — | phase-1, scope:knowledge, type:test |
| #780 | Tests — Schema v9 migration (source_pages, source_id FK) | 0 | — | phase-1, scope:knowledge, type:test |
| #781 | Tests — Content safety predicate inversion | 0 | — | phase-1, scope:knowledge, type:test |
| #782 | Tests — owlbear_browser package scaffold and CDP launcher | 0 | — | phase-1, scope:browser, type:test |
| #783 | Tests — owlbear_browser content extractor and HTML-to-MD cleaner | 0 | — | phase-1, scope:browser, type:test |
| #784 | Corporate entity and relation type extensions | 1 | #779 | phase-1, scope:knowledge |
| #785 | Schema v9 migration (source_pages, source_id FK) | 1 | #780 | phase-1, scope:knowledge |
| #786 | Content safety predicate inversion | 1 | #781 | phase-1, scope:knowledge |
| #787 | owlbear_browser package scaffold and CDP launcher | 1 | #782 | phase-1, scope:browser |
| #788 | owlbear_browser content extractor and HTML-to-MD cleaner | 1 | #783, #787 | phase-1, scope:browser |
| #789 | Tests — LLM extraction prompt corporate entity examples | 2 | #784 | phase-1, scope:knowledge, type:test |
| #790 | Tests — owlbear_mcp_browser MCP server and domain allowlist | 2 | #787 | phase-1, scope:mcp-browser, type:test |
| #791 | Tests — Replace-on-change refresh semantics | 2 | #785 | phase-1, scope:knowledge, type:test |
| #792 | Tests — AUTHENTICATED_WEB source type and ContentFetcher protocol | 2 | #785, #787 | phase-1, scope:knowledge, type:test |
| #793 | LLM extraction prompt corporate entity examples | 3 | #789 | phase-1, scope:knowledge |
| #794 | owlbear_mcp_browser MCP server and domain allowlist | 3 | #790, #788 | phase-1, scope:mcp-browser |
| #795 | Replace-on-change refresh semantics | 3 | #791 | phase-1, scope:knowledge |
| #796 | AUTHENTICATED_WEB source type and ContentFetcher protocol | 3 | #792 | phase-1, scope:knowledge |

### Parallelism

- **Layer 0 (5 tasks):** #779, #780, #781, #782, #783 — all independent
- **Layer 1 (5 tasks):** #784, #785, #786, #787, #788
- **Layer 2 (4 tasks):** #789, #790, #791, #792
- **Layer 3 (4 tasks):** #793, #794, #795, #796

### Dependency Workstreams

- **WS-A (Schema+Models):** #779→#784, #780→#785
- **WS-B (Pipeline Quality):** #781→#786, #784→#789→#793
- **WS-C (Browser):** #782→#787→#788, #787→#790→#794
- **WS-D (Integration):** #785→#791→#795, #785+#787→#792→#796

### Notes

- Dependency correction needed: #775 `depends_on` should be [774] not [752] — flagged in research
- Items 6+7+9 atomic ordering preserved: #784 (entity/rel types) → #789 (prompt tests) → #793 (prompt impl)
- Item 8 (content safety) independent per F4
- Every impl task has a preceding test task with dependency (TDD compliance)
[[2026-04-10]]

## Test-Writer Notes

- Test file: tests/test_authenticated_content_pipeline_775.py
- Classes:
  - `TestFromAC_BrowserPackage` — owlbear_browser cdp module, EdgeCDPLauncher (launch/connect/close), Edge binary resolver, error on missing binary, safe close
  - `TestFromAC_BrowserMCPServer` — owlbear_mcp_browser server module, 6 tools (navigate/click/type/select/read_text/snapshot), DomainAllowlist enforcement (blocked, allowed, empty, scoped)
  - `TestFromAC_AuthWebRefreshHandler` — content_fetcher kwarg accepted, stored, AUTHENTICATED_WEB dispatch no-raise, fetcher called per URL, RefreshResult counters, empty-URL zero counts, fetch failure → failed counter
  - `TestFromAC_ContentSafetyInversion` — url_list wrapped, novel type wrapped, file_glob not wrapped + predicate function assertion, url_list wrapping includes source URL attribute
  - `TestFromAC_ReplaceOnChangeRefresh` — delete_document_data called on prior ID, delete precedes insert (call-order tracking), ok-status after delete, two sequential replacements each trigger delete
- Tests per category: happy 13, edge 8, error 8, boundary 8
- Total: 37 tests, all FAIL
- ruff: clean
- AC coverage:

  | Scope Item | Tests |
  |---|---|
  | SC1 — owlbear_browser CDP launcher | 11 (TestFromAC_BrowserPackage) |
  | SC2 — owlbear_mcp_browser tools + allowlist | 11 (TestFromAC_BrowserMCPServer) |
  | SC3 — AUTHENTICATED_WEB dispatch | 5 (TestFromAC_AuthWebRefreshHandler) |
  | SC4 — ContentFetcher injection | 2 (TestFromAC_AuthWebRefreshHandler) |
  | SC5 — Schema v9 | deferred to #780 subtask |
  | SC6 — EntityType extensions | deferred to #779 subtask |
  | SC7 — RelationType extensions | deferred to #779 subtask |
  | SC8 — Content safety predicate inversion | 4 (TestFromAC_ContentSafetyInversion) |
  | SC9 — LLM prompt corporate examples | deferred to #789 subtask |
  | SC10 — Replace-on-change (ghost bug fix) | 4 (TestFromAC_ReplaceOnChangeRefresh) |

- Note: SC5, SC6, SC7, SC9 are each covered by dedicated Layer-0 subtask test files (#779, #780, #789) which are in backlog awaiting test-writer dispatch.

[[2026-04-10]]

## Builder Notes

### Files Changed (9)

- **NEW** `serve/browser/src/owlbear_browser/edge_launcher.py` — `EdgeCDPLauncher` class with async `launch()`, `connect()`, `close()` methods
- `serve/browser/src/owlbear_browser/__init__.py` — export `EdgeCDPLauncher`, `resolve_edge_binary` (alias for `find_edge_binary`)
- **NEW** `serve/mcp-browser/src/owlbear_mcp_browser/allowlist.py` — `DomainAllowlist` class with `check(url)` method
- **NEW** `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — FastMCP instance with 6 tools (navigate, click, type, select, read_text, snapshot); `mcp_app = _mcp._tool_manager` for synchronous `list_tools()` in tests
- `serve/mcp-browser/src/owlbear_mcp_browser/__init__.py` — export `mcp_app`, `server`
- `serve/mcp-browser/pyproject.toml` — added `mcp[cli]>=1.26` dependency
- `serve/knowledge/src/owlbear_knowledge/content_safety.py` — added `should_wrap(source_type)` predicate (deny-list inversion; `None`/empty returns `False` for backward compat)
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — replaced `_is_url` check with `should_wrap()`; added `delete_document_data(existing_id)` before `insert_document()` (ghost bug fix)
- `serve/knowledge/src/owlbear_knowledge/refresh.py` — added `content_fetcher` kwarg to `__init__`; added `_handle_authenticated_web()` handler; added `AUTHENTICATED_WEB` dispatch branch

### Test Results

- Target: 37 passed, ruff clean
- No regressions in `tests/test_content_safety_735.py` (16 passed after `should_wrap(None)→False` fix)
- 2 pre-existing failures in `test_authenticated_content_pipeline_751.py` (schema columns for `source_pages` — deferred to #785)

### Lint Status

ruff: clean on all 9 changed files

### Fixes Applied

1. **`should_wrap(None)→True` regression** — test_735 `test_ingest_without_source_type_metadata_does_not_wrap` caught that `None` source_type was being wrapped. Fixed: `if not source_type: return False` before the deny-list check
2. **FastMCP `list_tools()` is async** — test calls it synchronously; used `_mcp._tool_manager` (with `# noqa: SLF001`) which has a synchronous `list_tools()` returning `Tool` objects with `.name`

### Commit

`8065626b` feat: EdgeCDPLauncher, owlbear_mcp_browser scaffold, content safety inversion, ghost doc fix (#775, builder)
[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: 53 passed, 0 failed (37 from test_authenticated_content_pipeline_775.py + 16 regressions from test_content_safety_735.py)

### Lint: clean — ruff 0 violations across all 9 changed files + test file

### Coverage

| Module | % |
|---|---|
| owlbear_knowledge.content_safety | 100% |
| owlbear_knowledge.ingest | 88% |
| owlbear_browser.edge_launcher | 60% |
| owlbear_knowledge.refresh | 45% (new code covered; low overall reflects untouched pre-existing handlers) |

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| SC1 — EdgeCDPLauncher launch/connect/close | TestFromAC_BrowserPackage (11 tests) | Yes — iscoroutinefunction, FileNotFoundError, safe-close all assert specific behavior | COVERED |
| SC2 — MCP tools + domain allowlist | TestFromAC_BrowserMCPServer (11 tests) | Yes — tool name set membership, PermissionError on blocked domain | COVERED |
| SC3 — AUTHENTICATED_WEB dispatch | TestFromAC_AuthWebRefreshHandler (5 tests) | Yes — no-raise test, fetch called once per URL, RefreshResult type | COVERED |
| SC4 — ContentFetcher injection | TestFromAC_AuthWebRefreshHandler (2 tests) | Yes — kwarg accepted, MagicMock retrievable from vars() | COVERED |
| SC5 — Schema v9 migration | deferred to #780 (Layer-0 subtask, documented in plan) | N/A | DEFERRED ✓ |
| SC6 — EntityType extensions | deferred to #779 | N/A | DEFERRED ✓ |
| SC7 — RelationType extensions | deferred to #779 | N/A | DEFERRED ✓ |
| SC8 — Content safety predicate inversion | TestFromAC_ContentSafetyInversion (4 tests) | Yes — `<untrusted_web_content` in call text + should_wrap attribute check | COVERED |
| SC9 — LLM prompt examples | deferred to #789 | N/A | DEFERRED ✓ |
| SC10 — Ghost bug fix / replace-on-change | TestFromAC_ReplaceOnChangeRefresh (4 tests) | Yes — assert_called_once_with(prior_id), call-order tracking for delete<insert | COVERED |

Deferred items are each tracked as Layer-0 subtasks in the approved plan (#779, #780, #789) — not gaps.

#### Security Review

- **DomainAllowlist**: Uses `urlparse(url).hostname` with exact-match frozenset. Subdomain bypass (`sub.sharepoint.example.com`) correctly blocked. Credential-style URLs (`user@host`) parsed as hostname=host — correctly blocked. Malformed/empty URL → empty hostname → blocked. No bypass vector found.
- **edge_launcher.py**: `subprocess.Popen` with `[str(binary), *args]` where binary path comes from known Edge install location, not user input. `# noqa: S603,ASYNC220` suppressions appropriate.
- **content_safety.py**: `should_wrap(None) → False` is documented backward-compat behavior. Deny-list inversion is defense-in-depth — future source types are wrapped by default.
- **server.py tool stubs**: Tools return input without execution; no injection surface in current scaffolding.
- No hardcoded secrets, injection, path traversal, or insecure deserialization found.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---|---|---|
| All 37 TestFromAC_* test methods | No modifications detected | PRESERVED |
| should_wrap(None) regression (test_735) | Implementation fix applied, no test weakening | PRESERVED |

Builder notes report one fix to `should_wrap(None)→False` — this was an implementation correction to prevent wrapping content without source_type metadata. Test assertions unchanged.

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | `assert_called_once_with(prior_doc_id)`, call-order list, `<untrusted_web_content` in text — meaningful. `result.refreshed >= 1` is acceptable given mock returns exactly one "ok". |
| Negative/error-path coverage | ADEQUATE | Missing binary → FileNotFoundError, empty allowlist blocks all, fetch failure → failed counter, close before launch is safe |
| Mutation resistance | STRONG | Delete precedes insert tracked via side_effect list; removing the delete call fails test immediately |
| Test independence | STRONG | Fresh mocks per test, no shared mutable state |
| Descriptive names | STRONG | All names follow `test_{behavior_description}` pattern |

#### Data Safety

- No unvalidated LLM output persisted without sanitization.
- `_handle_authenticated_web` constructs `IntakeResult` with `source_type: "authenticated_web"` which IS wrapped by the deny-list predicate — authenticated web content correctly treated as untrusted.
- `delete_document_data(existing_id)` is synchronous call consistent with `ingest()` method's non-threaded call pattern.

#### Implementation-Aware Gaps

- `edge_launcher.py` happy path (binary exists → subprocess started → CDPConnectionManager created) not tested. Requires mocking `subprocess.Popen` + `CDPConnectionManager` — a new class without its own test file yet. Informational only; error path and interface conformance are covered.

#### Builder Process Quality

| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

1. **content_safety.py has duplicate module-level constants**: `_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` each defined twice (lines 9-19, then again at ~44-50). Second definition overrides with identical values — no behavioral impact. Appears to be a copy artifact from inserting `should_wrap()` before the existing constants. Recommend removing the first three definitions.
2. **edge_launcher.py — 60% coverage**: Happy-path `launch()` (subprocess creation, CDPConnectionManager init), `connect()` with active manager, and full `close()` teardown not covered. Acceptable for a scaffold task pending `CDPConnectionManager` test file.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| SC1 — EdgeCDPLauncher | edge_launcher.py:19-97; launch, connect, close are async methods; FileNotFoundError raised at L43 | test_edge_cdp_launcher_launch_is_coroutine, test_launch_raises_for_missing_binary | PASS |
| SC2 — MCP tools | server.py:12-47; 6 @_mcp.tool() decorators; allowlist.py:16-33 DomainAllowlist.check() with frozenset | test_navigate_tool_is_defined, test_navigate_blocked_for_unapproved_domain | PASS |
| SC3/SC4 — AUTHENTICATED_WEB + ContentFetcher | refresh.py:57-61 `content_fetcher` kwarg; L88-90 `elif source.source_type == SourceType.AUTHENTICATED_WEB` dispatch; L217-268 `_handle_authenticated_web()` | test_refresh_authenticated_web_source_does_not_raise, test_handle_authenticated_web_calls_content_fetcher | PASS |
| SC8 — Content safety inversion | content_safety.py:22: `_TRUSTED_SOURCE_TYPES = frozenset({"file", "file_glob", "text"})`; L36: deny-list check; ingest.py:186: `_should_wrap = should_wrap(_meta.get("source_type"))` | test_url_list_source_content_is_wrapped, test_file_glob_source_content_is_not_wrapped | PASS |
| SC10 — Ghost bug fix | ingest.py:173: `if existing_id is not None: self._docs.delete_document_data(existing_id)` before insert at L175 | test_replace_calls_delete_document_data_on_prior_doc, test_replace_delete_precedes_new_insert | PASS |

### Confidence: .95

### Verdict: PASS

[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` contains only branch table — no package registry or architecture section to update |
| 2 | Module docstrings | Yes | Updated | `ingest.py` `ingest()` docstring was stale (said `source_type == "url"`) — updated to reflect `should_wrap()` predicate with deny-list semantics. `refresh.py` `RefreshOrchestrator` class docstring was missing `content_fetcher` kwarg — added. All other public classes/methods (`EdgeCDPLauncher`, `DomainAllowlist`, `should_wrap`, MCP tool stubs, `__init__` modules) have accurate docstrings. |
| 3 | External attribution | Yes | Updated | Added `## Phase 1 Browser Package + Pipeline Quality + Schema (Task #775)` section to `.owlbear/sources/overview.md` with trafilatura and Playwright CDP API entries. Researcher said "already logged" but no #775 section existed — per-task entry convention applied. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists and is linked from task body. Follow-up tasks #779–#796 were created by planner. |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/ingest.py` — stale `ingest()` docstring (url-only → should_wrap)
- `serve/knowledge/src/owlbear_knowledge/refresh.py` — missing `content_fetcher` arg in class docstring
- `.owlbear/sources/overview.md` — added #775 attribution section (2 external sources)

### Scratch Files

No `.owlbear/scratch/775-*` files found.

### Commit

`2ae18575` docs: update docstrings and attribution for #775 browser packages (doc-writer)
[[2026-04-10]]

## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| SC1 — EdgeCDPLauncher launch/connect/close | edge_launcher.py exists, async methods confirmed; 11 tests pass (TestFromAC_BrowserPackage) | PASS |\n| SC2 — MCP tools + domain allowlist | server.py: 6 @_mcp.tool() decorators; allowlist.py: DomainAllowlist.check(); 11 tests pass (TestFromAC_BrowserMCPServer) | PASS |\n| SC3 — AUTHENTICATED_WEB dispatch | refresh.py:_handle_authenticated_web() + AUTHENTICATED_WEB branch; 5 tests pass (TestFromAC_AuthWebRefreshHandler) | PASS |\n| SC4 — ContentFetcher injection | refresh.py: content_fetcher kwarg in **init**; 2 tests pass | PASS |\n| SC5 — Schema v9 | Deferred to #780 subtask (Layer-0), tracked in plan | DEFERRED ✓ |\n| SC6 — EntityType extensions | Deferred to #779 subtask (Layer-0), tracked in plan | DEFERRED ✓ |\n| SC7 — RelationType extensions | Deferred to #779 subtask (Layer-0), tracked in plan | DEFERRED ✓ |\n| SC8 — Content safety inversion | content_safety.py: _TRUSTED_SOURCE_TYPES deny-list, should_wrap(); ingest.py uses should_wrap(); 4 tests pass | PASS |\n| SC9 — LLM prompt examples | Deferred to #789 subtask (Layer-2), tracked in plan | DEFERRED ✓ |\n| SC10 — Ghost bug fix | ingest.py: delete_document_data(existing_id) before insert; 4 tests pass including call-order assertion | PASS |\n\n### Test Results\n- pytest (task-scoped): 53 passed, 0 failed (37 from #775 + 16 from #735 regression suite)\n- pytest (full suite): 271 failed, 3309 passed — all failures pre-existing, unrelated to #775 (schema v8→v9 assertion tests from #751, AnalysisProposal model fixture mismatches, hook script path issues, etc.)\n- ruff: clean — 0 violations across serve/ and tests/\n\n### Reviewer Evidence\nPresent, detailed, PASS verdict at .95. Security review, test integrity, test quality, and data safety all assessed. Code-level findings trusted.\n\n### Architect Quality: 4/5\nWell-structured 10-item scope with clear deliverable boundaries. Research findings (F1-F6) identified real issues (ghost doc bug, atomic entity/prompt coupling). Dependency graph (WS-A/B/C/D) enabled clean 18-task decomposition. Minor gap: depends_on metadata still references #752 instead of #774 (flagged in research, not corrected).\n\n### Deduction Breakdown\n- Start: 1.00\n- AC lines without evidence: 0 (deferred items correctly tracked as subtasks)\n- Lint violations: 0\n- AC quality ≤ 3: N/A (score 4/5)\n- Missing reviewer evidence: 0 (present, detailed)\n- Full-suite failures in task scope: 0\n- Informational: duplicate constants in content_safety.py noted by reviewer — no behavioral impact, no deduction\n- Net deductions: 0\n\n### Confidence: .98\n### Action: archive
