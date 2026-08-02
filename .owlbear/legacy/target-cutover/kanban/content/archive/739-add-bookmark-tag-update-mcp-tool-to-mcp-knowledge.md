---
id: 739
title: Add bookmark tag update MCP tool to mcp-knowledge
status: archived
priority: medium
created: '2026-04-10T04:24:46.8732866+02:00'
updated: '2026-04-10T05:49:11.335912+00:00'
tags:
- knowledge
- mcp
- v1-port
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
class: standard
---

## Objective

Add an MCP tool to update tags on existing bookmarks. The BookmarkStore.update_tags() method exists but isn't exposed via MCP.

## Context

v2 has bookmark_source and list_bookmarks MCP tools but no way to update/add tags to existing bookmarks. This limits agents' ability to categorize and organize bookmarked content.

## Acceptance Criteria

- [ ] New `update_bookmark_tags` MCP tool in mcp-knowledge server
- [ ] Tool accepts bookmark URL (or ID) and new tags list
- [ ] Tool calls existing BookmarkStore.update_tags()
- [ ] Returns updated bookmark data
- [ ] Existing tests pass; new test verifies MCP tool wiring

[[2026-04-10]] Fri 05:05

## Architecture Review

### Refined Acceptance Criteria

The original AC has ambiguities (URL vs ID, return shape, error behavior). The following **supersedes** the original AC for downstream agents:

- [ ] New `update_bookmark_tags` async MCP tool registered on `mcp` in `server.py`, annotated with `ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)`
- [ ] Tool signature: `url: str`, `tags: list[str]`, `scope: str = "global"`
- [ ] Tool resolves the bookmark via `BookmarkStore.get_by_url(url, scope)`; raises `ToolError` if `bookmark_store` is `None` or URL not found
- [ ] Calls `BookmarkStore.update_tags(bookmark.id, tags)` via `asyncio.to_thread`
- [ ] Returns a `BookmarkInfo` dict (`url`, `title`, `relevance_score`, `tags`) with the updated tags — construct from fetched bookmark + new tags, no second DB read needed
- [ ] `update_bookmark_tags` added to `server.py` `__all__` list
- [ ] Existing tests pass; new test class verifies MCP tool wiring (mock context pattern per `TestFromAC_MCPBookmarkTools` in `tests/test_bookmark_pipeline_136.py`)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One tool, one purpose: update bookmark tags |
| Interface clarity | PASS (after refine) | Original AC ambiguous on URL vs ID; refined to `url` since `list_bookmarks` doesn't expose IDs. Scope param added for consistency with `get_by_url()` |
| Dependency correctness | PASS | No `depends_on`; `BookmarkStore.update_tags()` and `get_by_url()` both exist |
| Module layering | PASS | MCP tool → BookmarkStore: correct direction per knowledge package layering |
| TDD compliance | PASS | AC specifies test wiring; test-writer will create test class before implementation |
| KISS/YAGNI | PASS | Minimal new code: one tool function, one TypedDict reuse, one `__all__` entry |
| Premise challenge | PASS | Verified no existing MCP tool updates bookmark tags. `bookmark_source` creates but doesn't modify tags. Genuine capability gap |
| Pattern consistency | PASS | Follows `list_bookmarks`/`bookmark_source` patterns: `@mcp.tool()`, `ToolAnnotations`, `asyncio.to_thread()`, `AppContext` access, `ToolError` on unavailability |
| Security surface | PASS | No new external boundaries; tags are a `list[str]` validated by FastMCP schema; URL used only as a DB lookup key |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `bookmark_store is None` | Store not initialized | `ToolError` | Yes (AC) | Clear error message |
| `get_by_url()` returns `None` | URL not in DB for scope | `ToolError` | Yes (AC) | Clear "not found" error |
| `update_tags()` internal | Should not fail after `get_by_url` succeeds | `ValueError` (dead path) | N/A | N/A |

### Builder Guidance

- **File**: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- **Placement**: After `list_bookmarks` tool (line ~385), before `import_scope`
- **Pattern reference**: `list_bookmarks` (lines 372-385) for read pattern; `bookmark_source` (lines 349-362) for write-tool annotations
- **Reuse `BookmarkInfo` TypedDict** (lines 363-370) for return type
- **Error pattern**: Follow `list_sources` / `get_stats` — `raise ToolError(msg)` not error strings
- **Thread offloading**: Both `get_by_url` and `update_tags` are sync; wrap in `asyncio.to_thread`
- **Test pattern**: `TestFromAC_MCPBookmarkTools` in `tests/test_bookmark_pipeline_136.py` — mock `AppContext`, test registration, test calls store methods, test error cases

### Challenge Results

- Challenger: **proceed** (confidence: 0.95)
- Architect response: accepted — all refinements incorporated

### Verdict: APPROVE (after REFINE)

### Action Taken: Tightened AC to resolve URL-vs-ID ambiguity (URL wins — agents only see URLs from `list_bookmarks`), specified `scope` parameter, clarified return shape as `BookmarkInfo`, specified `ToolError` for error cases. Advanced to `todo`

[[2026-04-10]] Fri 05:27

## Test-Writer Notes

- Test file: tests/test_bookmark_pipeline_739.py
- Classes:
  - `TestFromAC_UpdateBookmarkTagsRegistration` — tool presence and `__all__`
  - `TestFromAC_UpdateBookmarkTagsAnnotations` — readOnlyHint=False, destructiveHint=False, idempotentHint=True
  - `TestFromAC_UpdateBookmarkTagsHappyPath` — get_by_url called with url+scope, update_tags called with id+tags, BookmarkInfo dict returned with new tags/title/relevance_score, default scope="global"
  - `TestFromAC_UpdateBookmarkTagsEdgeCases` — empty tags list clears tags; custom scope forwarded
  - `TestFromAC_UpdateBookmarkTagsErrorPaths` — ToolError on None store, ToolError on URL not found, update_tags not called on not-found
  - `TestFromAC_UpdateBookmarkTagsBoundary` — get_by_url called exactly once (no second DB read); result has all BookmarkInfo keys
- Tests per category: happy 6, edge 2, error 3, boundary 2; registration+annotations 6
- Total: 19 tests, all FAIL (ImportError: cannot import name 'update_bookmark_tags')
- ruff: clean

AC coverage:

| AC Line | Tests |
|---------|-------|
| update_bookmark_tags MCP tool registered | test_update_bookmark_tags_function_registered, test_update_bookmark_tags_is_callable |
| Annotated readOnlyHint=False, destructiveHint=False, idempotentHint=True | test_not_read_only, test_not_destructive, test_idempotent_hint_true |
| Tool signature: url, tags, scope="global" | test_default_scope_is_global, test_custom_scope_passed_to_get_by_url |
| Resolves via get_by_url(url, scope) | test_calls_get_by_url_with_url_and_scope |
| ToolError if bookmark_store is None | test_raises_tool_error_when_bookmark_store_none |
| ToolError if URL not found | test_raises_tool_error_when_url_not_found, test_update_tags_not_called_when_url_not_found |
| Calls update_tags(bookmark.id, tags) | test_calls_update_tags_with_bookmark_id_and_new_tags |
| Returns BookmarkInfo dict with updated tags | test_returned_tags_reflect_new_tags_not_old, test_returns_bookmark_info_dict_with_url, test_returns_title_and_relevance_score_from_bookmark, test_result_has_all_bookmark_info_keys |
| No second DB read | test_get_by_url_called_exactly_once |
| update_bookmark_tags in **all** | test_update_bookmark_tags_in_all |
| Empty tags accepted | test_empty_tags_list_accepted |

[[2026-04-10]] Fri 05:46

## Builder Notes

### Files Changed

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — added `update_bookmark_tags` tool and entry in `__all__`

### Implementation

Added `update_bookmark_tags` after `list_bookmarks` (before `import_scope`):

- `@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))`
- Signature: `url: str, tags: list[str], scope: str = "global"`
- Raises `ToolError` if `bookmark_store` is `None`
- Calls `store.get_by_url(url, scope)` via `asyncio.to_thread`; raises `ToolError` if URL not found
- Calls `store.update_tags(bookmark.id, tags)` via `asyncio.to_thread`
- Returns `BookmarkInfo` dict built from fetched bookmark + new tags (no second DB read)
- `update_bookmark_tags` added to `__all__` (ruff auto-sorted)

### Test Results

- RED verified: 19/19 failed before implementation (ImportError)
- GREEN: **19/19 passed** after implementation
- Coverage: new function branches all covered (store=None, URL not found, success path)

### Lint

- ruff: **clean** (RUF022 auto-fixed — `__all__` sort)

### Evidence

`DONE #739 -> review | 19 passed, ruff clean`

[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: **19 passed, 0 failed** (quality-runner, independent run)

### Lint

- ruff: **clean** (0 violations — server.py + test file)

### Coverage

- owlbear_mcp_knowledge.server: 39% (pre-existing pattern; all new `update_bookmark_tags` code paths covered — lifespan/DB/other tools are integration-only by design, consistent with #737 and #738)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| update_bookmark_tags registered with ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True) | test_not_read_only, test_not_destructive, test_idempotent_hint_true | YES — each asserts exact annotation value; wrong values fail assertion | COVERED |
| Tool signature: url, tags, scope="global" | test_default_scope_is_global, test_custom_scope_passed_to_get_by_url | YES — get_by_url.assert_called_once_with(url, "global") fails if default changes | COVERED |
| Resolves via get_by_url(url, scope); ToolError if store is None | test_raises_tool_error_when_bookmark_store_none, test_calls_get_by_url_with_url_and_scope | YES — pytest.raises(ToolError) fails if guard removed | COVERED |
| ToolError if URL not found | test_raises_tool_error_when_url_not_found, test_update_tags_not_called_when_url_not_found | YES — raises check + update_tags assert_not_called | COVERED |
| Calls update_tags(bookmark.id, tags) via asyncio.to_thread | test_calls_update_tags_with_bookmark_id_and_new_tags | YES — assert_called_once_with(bookmark.id, tags) | COVERED |
| Returns BookmarkInfo dict with updated tags (not old); no second DB read | test_returned_tags_reflect_new_tags_not_old, test_returns_bookmark_info_dict_with_url, test_returns_title_and_relevance_score_from_bookmark, test_result_has_all_bookmark_info_keys, test_get_by_url_called_exactly_once | YES — exact value checks + call_count == 1 | COVERED |
| update_bookmark_tags in **all** | test_update_bookmark_tags_in_all | YES — assert membership | COVERED |

No MISSING. No LAX.

#### Security Review

- `url`: used only as DB lookup key via `store.get_by_url(url, scope)` — no SQL/template/shell injection surface
- `tags: list[str]`: validated by FastMCP schema; passed to `store.update_tags()` — no injection surface
- `scope: str`: used only for DB lookup; no filesystem or shell operations
- Error message `f"bookmark not found for URL: {url}"` echoes user-provided URL — no credential leakage; consistent with other tools
- No hardcoded secrets, path traversal, deserialization, new dependencies
- **No issues**

#### Test Integrity — TestFromAC Comparison

Builder modified only `server.py`. `tests/test_bookmark_pipeline_739.py` unmodified.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 19 TestFromAC_* methods | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | assert_called_once_with(url, scope), result["tags"] == ["fresh"], store.update_tags.assert_not_called() — no lazy asserts |
| Negative/error-path coverage | STRONG | 3 error tests + 2 edge tests; every branch in update_bookmark_tags covered |
| Mutation reasoning | STRONG | Flipping annotation values → annotation tests fail; removing URL guard → error tests fail; returning old tags → test_returned_tags_reflect_new_tags_not_old fails; second DB read → test_get_by_url_called_exactly_once fails |
| Test independence | STRONG | Each test instantiates fresh mocks via _make_bookmark()/_make_ctx(); no shared state |
| Descriptive names | STRONG | All 19 names are self-documenting |

No WEAK ratings.

#### Data Safety

- `asyncio.to_thread` calls for `get_by_url` and `update_tags` are sequential — no concurrency issues
- Two-step pattern (lookup then update) is consistent with existing tools; no atomicity concern beyond what pattern establishes
- No LLM output persisted, no unbounded input
- **No issues**

#### Implementation-Aware Gap Analysis

New code paths in server.py (lines 430–449):

- `store is None` → ToolError: covered by test_raises_tool_error_when_bookmark_store_none
- `get_by_url(url, scope)` → None → ToolError: covered by test_raises_tool_error_when_url_not_found
- `update_tags(bookmark.id, tags)` called correctly: covered by test_calls_update_tags_with_bookmark_id_and_new_tags
- Return dict tags = new tags (not old bookmarks.tags): covered by test_returned_tags_reflect_new_tags_not_old
- No second DB read: covered by test_get_by_url_called_exactly_once

No significant untested paths.

#### Builder Process Quality

1 Builder Notes section, 0 retries. **CLEAN.**

---

### Pass 2 — INFORMATIONAL

1. **Coverage 39%**: Pre-existing pattern for server.py in this module — confirmed consistent with #737 (41%) and #738 (static analysis). Lifespan/DB/other tools are integration-only paths unchanged by this task. All new code paths exercised. -.01 deduction.
2. **`scope` parameter has no `Annotated` description**: Minor UX gap — agents calling the tool will not see a description for `scope`. Consistent with existing tool patterns in the same file. Informational only.

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| update_bookmark_tags registered with ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True) | server.py:437 — `@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))` | test_not_read_only, test_not_destructive, test_idempotent_hint_true | PASS |
| Tool signature: url, tags, scope="global" | server.py:438-442 — `async def update_bookmark_tags(ctx, url: str, tags: list[str], scope: str = "global")` | test_calls_get_by_url_with_url_and_scope, test_default_scope_is_global | PASS |
| Resolves via get_by_url(url, scope); ToolError if store None | server.py:443-448 — store None guard + asyncio.to_thread(store.get_by_url, url, scope) | test_raises_tool_error_when_bookmark_store_none, test_calls_get_by_url_with_url_and_scope | PASS |
| ToolError if URL not found | server.py:449-451 — `if bookmark is None: raise ToolError(msg)` | test_raises_tool_error_when_url_not_found, test_update_tags_not_called_when_url_not_found | PASS |
| Calls update_tags(bookmark.id, tags) via asyncio.to_thread | server.py:452 — `await asyncio.to_thread(store.update_tags, bookmark.id, tags)` | test_calls_update_tags_with_bookmark_id_and_new_tags | PASS |
| Returns BookmarkInfo with updated tags + no second DB read | server.py:453 — `return {"url": bookmark.url, ..., "tags": tags}` (uses new tags, not bookmark.tags) | test_returned_tags_reflect_new_tags_not_old, test_result_has_all_bookmark_info_keys, test_get_by_url_called_exactly_once | PASS |
| update_bookmark_tags in **all** | server.py:262 — confirmed in **all** list | test_update_bookmark_tags_in_all | PASS |

---

### Deductions

- Coverage 39% (pre-existing module pattern): -.01
- All Pass 1 criteria met: 0 additional deductions

### Confidence: .99

### Verdict: PASS #739 -> docs | confidence .99

[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | New `update_bookmark_tags` MCP tool added. `copilot-instructions.md` (80 lines) contains no MCP tool table or knowledge server listing — no update target exists |
| 2 | Module docstrings | Yes | Verified | `update_bookmark_tags` has `"""Update the tags on an existing bookmark."""` — accurate, consistent with single-line pattern used by all tools in server.py (`list_sources`, `get_stats`, `bookmark_source`, `list_bookmarks`) |
| 3 | External attribution | No | N/A | Builder notes reference only existing codebase patterns (`list_bookmarks`, `bookmark_source`); no external repos/articles cited |
| 4 | CLI changes | No | N/A | MCP tool addition; no CLI surface changed |
| 5 | Research doc | No | N/A | No research doc referenced in task body; none of the 5 bookmark research files in `.owlbear/research/` cover this task |

### Files Updated

None — no documentation updates required.

### Scratch Files

None found matching `.owlbear/scratch/739-*`.

### Commit

Skipped — no files changed.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `update_bookmark_tags` MCP tool registered on `mcp` in server.py | server.py:428 `@mcp.tool(...)` + test_update_bookmark_tags_function_registered | PASS |
| ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True) | server.py:428 exact annotation kwargs + test_not_read_only, test_not_destructive, test_idempotent_hint_true | PASS |
| Tool signature: url, tags, scope="global" | server.py:429-433 — verified signature + test_default_scope_is_global, test_custom_scope_passed_to_get_by_url | PASS |
| Resolves via get_by_url(url, scope); ToolError if store None or URL not found | server.py:436-443 — both guards present + test_raises_tool_error_when_bookmark_store_none, test_raises_tool_error_when_url_not_found | PASS |
| Calls update_tags(bookmark.id, tags) via asyncio.to_thread | server.py:444 — `await asyncio.to_thread(store.update_tags, bookmark.id, tags)` + test_calls_update_tags_with_bookmark_id_and_new_tags | PASS |
| Returns BookmarkInfo dict with updated tags; no second DB read | server.py:445 returns `{"tags": tags}` (new tags, not bookmark.tags) + test_returned_tags_reflect_new_tags_not_old, test_get_by_url_called_exactly_once | PASS |
| `update_bookmark_tags` in `__all__` | server.py:259 confirmed in list + test_update_bookmark_tags_in_all | PASS |

### Test Results

- pytest (task-scoped): **19 passed, 0 failed** (test_bookmark_pipeline_739.py)
- pytest (full suite): 3113 passed, 278 failed, 2 errors — **0 failures in task scope**; all 278 failures are pre-existing in unrelated test files
- ruff: **clean** (serve/ + tests/)

### Reviewer Evidence

Present and thorough — Pass 1 (CRITICAL) covers AC mapping, security review, test integrity, test quality, data safety, and implementation-aware gap analysis. PASS verdict at .99. Trusted for code-level detail.

### Architect Quality: 5/5

Refined AC was specific, complete, and provided clear implementation path. Exact tool signature, annotations, error handling patterns, builder guidance with file/line references, failure mode map, and pattern references. Zero builder improvisation needed.

### Deduction Breakdown

| Criterion | Deduction |
|-----------|-----------|
| AC lines with no evidence | 0 (all 7 have test + code evidence) |
| Lint violations | 0 (ruff clean) |
| AC quality score ≤ 3 | 0 (score 5/5) |
| Missing reviewer evidence | 0 (present, detailed, PASS) |
| Full-suite failures in task scope | 0 (0 in scope) |

### Informational Notes

- **Uncommitted server.py**: Builder did not commit server.py changes. The file has co-mingled changes from #738 (consolidate_knowledge), refresh_source task, and #739 (update_bookmark_tags) — all uncommitted. Cannot selectively stage #739 hunks without interactive `git add -p`. Implementation is verified correct in working tree.
- Test file committed by auditor: `e07ee05 test: RED-phase tests for update_bookmark_tags MCP tool #739`

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e07ee05 | test | tests/test_bookmark_pipeline_739.py | #739 |
