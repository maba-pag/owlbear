---
id: 886
title: Remove Graph API SharePoint code — dead path per v1 auth failure
status: archived
priority: medium
created: '2026-04-15T12:41:52.520931+00:00'
updated: '2026-04-15T20:04:50.618644+00:00'
tags:
- scope:knowledge
- type:config
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Graph API SharePoint extraction was fully implemented (task 879) but the authentication prerequisite (Azure AD app registration from corporate IT, task 878) is not viable — v1 exploration confirmed auth cannot be obtained in the corporate environment.

## Acceptance Criteria

- Delete `serve/knowledge/src/owlbear_knowledge/graph_fetcher.py`
- Remove `SourceType.SHAREPOINT_API` from `models.py`
- Remove `_handle_sharepoint_api()` and `graph_content_fetcher` parameter from `refresh.py` and `RefreshOrchestrator`
- Remove or update associated tests (tasks 880-885 test coverage)
- Archive task 878 as won't-do
- Update any docs referencing SharePoint API extraction

## Context

- Parent research: task 773 (Phase 4, optional)
- Implementation: task 879 (28 tests, all passing)
- Blocker: task 878 (IT approval, non-viable)
- Playwright browser path is the deployed solution and works

[[2026-04-15]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single logical change: remove dead Graph API SharePoint code path. All AC items are coupled — removing the module without removing references would break the build. |
| Interface clarity | REFINE | See refined AC below — original AC missed pyproject.toml cleanup, was vague on test files, and omitted the `graph_fetcher` backward-compat alias |
| Dependency correctness | PASS | No upstream dependencies. Removal-only. |
| Module layering | PASS | Removal only — no new imports or layer violations |
| TDD compliance | PASS | No new code = no new tests. Existing tests will be deleted. `type:config` tag signals pass-through to test-writer. |
| KISS/YAGNI | PASS | This IS YAGNI cleanup — removing code for an unachievable auth prerequisite |
| Premise challenge | PASS | Task 878 confirms Azure AD app registration is non-viable in corporate environment. Playwright browser path is the deployed solution. |
| Pattern consistency | PASS | Standard code removal pattern |
| Security surface | PASS | Removal reduces attack surface (removes MSAL/Azure AD auth code, `msal` dependency) |
| Single domain | PASS | scope:knowledge only |

### AC Assessment (original)

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Delete `graph_fetcher.py` | Clear and verifiable | No change |
| Remove `SourceType.SHAREPOINT_API` from `models.py` | Clear and verifiable | No change |
| Remove `_handle_sharepoint_api()` and `graph_content_fetcher` param from `refresh.py` | Incomplete — also need to remove `graph_fetcher` backward-compat alias and its fallback logic at L90 | Refined below |
| Remove or update associated tests (tasks 880-885) | Vague — which test files? | Refined to list 3 specific files |
| Archive task 878 as won't-do | Not builder work — kanban operational action | Moved to separate follow-up note |
| Update any docs referencing SharePoint API extraction | Vague scope | Refined: research docs are historical, no code docs reference this feature |

### Refined AC (builder should follow this)

1. Delete `serve/knowledge/src/owlbear_knowledge/graph_fetcher.py`
2. Remove `SHAREPOINT_API = "sharepoint_api"` from `serve/knowledge/src/owlbear_knowledge/models.py` (SourceType enum, L51)
3. In `serve/knowledge/src/owlbear_knowledge/refresh.py`:
   - Remove `graph_content_fetcher: object | None = None` parameter from `__init__` (L81)
   - Remove `graph_fetcher: object | None = None` backward-compat alias parameter (L82)
   - Remove `self._graph_content_fetcher` assignment (L90)
   - Remove docstring lines referencing `graph_content_fetcher` / SharePoint (L60-63)
   - Remove the `elif source.source_type == SourceType.SHAREPOINT_API:` dispatch branch (L120-121)
   - Remove the entire `_handle_sharepoint_api()` method (L307-367)
4. In `serve/knowledge/pyproject.toml`:
   - Remove `sharepoint = ["msal>=1.27", "httpx>=0.27"]` optional dependency (L16)
   - Remove `"msal>=1.27",` from `full` extras (L22)
5. Delete test files:
   - `tests/test_graph_fetcher_879.py`
   - `tests/test_refresh_sharepoint_879.py`
   - `tests/test_sharepoint_api_dispatch_885.py`
6. Verify: all remaining tests pass (`uv run pytest tests/ -m "not api" -q`)

### Items NOT in builder scope

- Archive task 878 — orchestrator/user action, not code work
- Docs: research docs (`.owlbear/research/773-*.md`, `879-*.md`, `878-*.md`) are historical records, not live docs — do not modify
- `serve/browser/src/owlbear_browser/cleaner.py` SharePoint boilerplate removal is for the Playwright browser path (different feature, stays)
- `tests/test_sharepoint_normalization_829.py` is browser-path SharePoint normalization (different feature, stays)

### Challenge Results

- Challenger: FALLBACK — challenger agent not in available subagent list
- Architect response: proceeding on criteria analysis; removal task with clear codebase evidence

### Verdict: APPROVE

### Action Taken: Approved with refined AC. Original AC tightened to specify exact files, line ranges, pyproject.toml cleanup, and backward-compat alias removal. Task 878 archival removed from builder scope. Tagged `type:config` (pass-through for test-writer)

[[2026-04-15]]

## Test-Writer Notes

- Non-implementation task (tagged `type:config`) — no tests applicable.
- AC describes code deletion only: delete `graph_fetcher.py`, remove `SourceType.SHAREPOINT_API`, remove `_handle_sharepoint_api()` and related params from `refresh.py`, remove `msal` optional dependency from `pyproject.toml`, and delete 3 test files (`test_graph_fetcher_879.py`, `test_refresh_sharepoint_879.py`, `test_sharepoint_api_dispatch_885.py`).
- Architecture review confirms: "No new code = no new tests." Removal-only task.
- Passing through to builder.
[[2026-04-15]]

## Builder Notes

- All AC items were already completed in prior work (likely from the task 879 rollback).
- Verified: `graph_fetcher.py` — does not exist; `SourceType.SHAREPOINT_API` — not in models.py; `_handle_sharepoint_api` / `graph_content_fetcher` — not in refresh.py; `sharepoint` optional dep + `msal` — not in serve/knowledge/pyproject.toml; test files `test_graph_fetcher_879.py`, `test_refresh_sharepoint_879.py`, `test_sharepoint_api_dispatch_885.py` — all deleted.
- Full test run: 4327 passed, 195 failed (all pre-existing, zero related to sharepoint/graph_fetcher/SourceType/msal), 8 skipped.
- Ruff: no issues found on knowledge package files.
- No code changes made — all deletions were already applied.
- Files changed: 0 (removal-only, already completed).
[[2026-04-15]]

## Review Evidence

### Source Control Changes

Builder reported 0 files changed (removal-only; deletions already applied before builder claimed task). Verified independently.

### Tests

pytest: **811 passed, 6 failed, 1 skipped**

- Zero failures related to sharepoint / graph_fetcher / SHAREPOINT_API / msal
- 6 pre-existing failures (orchestrator routing: `test_auditor_wave_fills_with_light_flex_priority_order`, `test_decomp_override_routes_agent_to_kanban_planner`; skill validation: `test_existing_skill_passes_enhanced_validation[w-dispatch-planning]`; setup config: `test_setup_source_contains_owlbear_memory_key`; agent tools: `test_script_exits_zero_on_current_agents`, `test_tools_list_does_not_contain_edit_slash_edit_files`) — all pre-existing, scope:knowledge removal has no causal relationship

### Lint

`ruff` on `serve/knowledge/src/` and `serve/knowledge/pyproject.toml`: **clean, 0 violations**

### TestFromAC Classes

None (type:config tag, removal-only task — conditional steps 5.0 and 5.2 skipped per skill)

### AC Compliance Table

| AC Line (refined) | Evidence | Status |
|---|---|---|
| Delete `graph_fetcher.py` | `file_search **/graph_fetcher.py` → no results | PASS |
| Remove `SHAREPOINT_API` from `models.py` | `SourceType` enum contains only `URL_LIST`, `FILE_GLOB`, `AUTHENTICATED_WEB` (models.py lines 1–55 read) | PASS |
| Remove `graph_content_fetcher` param from `refresh.py` | grep across all `*.py` files → zero matches for `graph_content_fetcher` or `graph_fetcher` | PASS |
| Remove `graph_fetcher` backward-compat alias from `refresh.py` | Same grep — zero matches | PASS |
| Remove `_handle_sharepoint_api()` from `refresh.py` | Zero matches across codebase | PASS |
| Remove SharePoint docstring lines from `RefreshOrchestrator` | refresh.py L60–80 read — docstring only references `AUTHENTICATED_WEB`, no SharePoint API mention | PASS |
| Remove `elif source.source_type == SourceType.SHAREPOINT_API:` dispatch branch | `SHAREPOINT_API` zero matches in all Python files | PASS |
| Remove `sharepoint` optional dep from `serve/knowledge/pyproject.toml` | pyproject.toml read in full — no `sharepoint` extra, no `msal` | PASS |
| Remove `msal>=1.27` from `full` extras | Confirmed absent from knowledge pyproject.toml (`msal` remains in root pyproject.toml dev deps only — not in scope) | PASS |
| Delete `tests/test_graph_fetcher_879.py` | `file_search` → no results | PASS |
| Delete `tests/test_refresh_sharepoint_879.py` | `file_search` → no results | PASS |
| Delete `tests/test_sharepoint_api_dispatch_885.py` | `file_search` → no results | PASS |

### Residual Reference Scan

- `SHAREPOINT_API` / `graph_fetcher` / `graph_content_fetcher` / `_handle_sharepoint_api`: **zero matches** across all Python files
- 84 matches for `sharepoint` remain — all benign: browser HTML cleaner (`cleaner.py`, `test_cleaner_756.py`, `test_sharepoint_normalization_829.py`), test fixture URLs (`test_cdp_spike_*.py`, `test_contentfetcher_impl_830.py`, `test_fetcher_playwright_872.py`), domain allowlist tests — none related to Graph API

### Security Review

Removal-only task. No new code introduced. MSAL/Azure AD auth code removed = reduced attack surface. No security concerns.

### Deductions

None.

### Confidence: .97 → PASS

[[2026-04-15]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `SourceType.SHAREPOINT_API` removed from `models.py`. `copilot-instructions.md` contains zero matches for `sharepoint`, `graph_fetcher`, `SHAREPOINT_API`, `msal` — no table or section documents this enum. No update needed. |
| 2 | Module docstrings | Yes | Verified | `refresh.py` docstring read (L47–75): describes only `AUTHENTICATED_WEB`, no SharePoint API references. `models.py` `SourceType` docstring: clean. `graph_fetcher.py` deleted — no orphan docstrings. |
| 3 | External attribution | No | N/A | Removal-only task. No new external patterns or libraries introduced. `sources/overview.md` unchanged. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. README.md contains zero matches for `graph_fetcher`/`sharepoint_api`. |
| 5 | Research doc | No | N/A | No research doc produced for task #886 (removal task). Parent research docs `773-sharepoint-rest-api-parallel-path.md` and `879-graphcontentfetcher-implementation.md` are historical records per architecture review — do not modify. |

### Files Updated

- None

### Scratch Files Cleaned

- None (file_search for `.owlbear/scratch/886-*` returned no results)
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Delete `graph_fetcher.py` | file_search → no results | PASS |
| Remove `SHAREPOINT_API` from `models.py` | grep zero matches in models.py | PASS |
| Remove `graph_content_fetcher` param from `refresh.py` | grep zero matches across all *.py | PASS |
| Remove `graph_fetcher` backward-compat alias | grep zero matches across all *.py | PASS |
| Remove `_handle_sharepoint_api()` | grep zero matches across all *.py | PASS |
| Remove SharePoint docstring lines from `RefreshOrchestrator` | diff confirmed 4 docstring lines removed | PASS |
| Remove `elif SourceType.SHAREPOINT_API:` dispatch branch | diff confirmed 2 lines removed | PASS |
| Remove `sharepoint` optional dep from pyproject.toml | grep zero matches in knowledge pyproject.toml | PASS |
| Remove `msal>=1.27` from `full` extras | diff confirmed removal | PASS |
| Delete `test_graph_fetcher_879.py` | file_search → no results | PASS |
| Delete `test_refresh_sharepoint_879.py` | file_search → no results | PASS |
| Delete `test_sharepoint_api_dispatch_885.py` | file_search → no results | PASS |

### Test Results

- pytest: 4325 passed, 193 failed (all pre-existing, zero sharepoint/graph-related), 8 skipped
- ruff: clean on serve/knowledge/; 1 pre-existing E501 in serve/kanban/ (out of scope)

### Architect Quality: 4/5

Original AC was somewhat vague ("Remove or update associated tests" without naming files). Architect refined well: specific files, line ranges, pyproject.toml cleanup, backward-compat alias, and clear exclusion list (browser-path sharepoint stays). Minor gap: original AC included "Archive task 878" which is not builder work — architect correctly moved it out of scope.

### Deduction Breakdown

None. All 12 AC lines have specific evidence. Reviewer evidence detailed with residual reference scan. No lint violations in scope. No task-scoped test failures.

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a342b897 | chore | graph_fetcher.py, models.py, refresh.py, knowledge/pyproject.toml, 3 test files (7 files, 1918 deletions) | #886 |
