# Playwright Dependency Bump for aria_snapshot Support

> **Owning task:** #855 — Bump playwright dependency to >=1.59.0 for aria_snapshot support
> **Date:** 2026-04-13  **Status:** Complete (blocked finding)

## 1. Context and Question

Task #855 (from #837 §3f) requires bumping `playwright>=1.40` to `>=1.59.0` in `serve/browser/pyproject.toml` to enable `page.aria_snapshot()` for the `snapshot()` MCP tool. Is this feasible today, and are there breaking changes to consider?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | Playwright Python release notes (playwright.dev/python/docs/release-notes) | 1.0 |
| 2 | PyPI release history (pypi.org/project/playwright/#history) | 1.0 |
| 3 | serve/browser/pyproject.toml (current dep) | .95 |
| 4 | uv.lock (resolved version) | .95 |
| 5 | .owlbear/research/837-mcp-browser-session-management.md §3f | .90 |
| 6 | serve/mcp-browser/src/owlbear_mcp_browser/server.py (snapshot stub) | .85 |
| 7 | tests/test_mcp_browser_session_837.py (aria_snapshot mock) | .85 |

## 3. Analysis

### 3a. API Introduction Versions

| API | Introduced | Verified Source |
|-----|-----------|-----------------|
| `locator.aria_snapshot()` | v1.49 | Release notes §1.49 "Aria snapshots" |
| `page.aria_snapshot()` | v1.59 | Release notes §1.59 "Snapshots and Locators" |

### 3b. Availability

| Package | Latest on PyPI | `page.aria_snapshot()` available? |
|---------|---------------|----------------------------------|
| playwright (Python) | 1.58.0 (2026-01-30) | **No** — v1.59 not yet released |
| playwright (Node.js npm) | 1.59.1 (~2026-04-04) | Yes |

**Blocker:** Specifying `playwright>=1.59.0` would cause `uv lock` to fail — no such Python version exists. AC item 2 ("uv lock succeeds") is currently infeasible.

### 3c. Current State

- `serve/browser/pyproject.toml`: `playwright>=1.40`
- `uv.lock` resolved: `playwright==1.58.0`
- `snapshot()` tool in server.py: stub returning `""`
- Tests mock `page.aria_snapshot` but no production code calls it yet

### 3d. Breaking Changes (v1.40 → v1.58)

| Version | Breaking Change | Affects Us? |
|---------|----------------|-------------|
| v1.49 | Python 3.8 dropped | No (we use >=3.12) |
| v1.52 | Glob patterns in `page.route()` | No (not used) |
| v1.57 | `page.accessibility` removed | No (not used) |
| v1.58 | `_react`/`_vue` selectors removed | No (not used) |
| v1.58 | `devtools` launch option removed | No (we use `connect_over_cdp`) |

No breaking changes affect our codebase.

### 3e. Alternative Approach

| Criterion | Option A: `>=1.59.0` | Option B: `>=1.49.0` |
|-----------|----------------------|----------------------|
| API | `page.aria_snapshot()` | `page.locator('body').aria_snapshot()` |
| Available now? | **No** — blocked on PyPI | **Yes** — already resolved |
| Lock change | Fails | No change (1.58.0 satisfies) |
| Code complexity | Simpler | One extra `.locator('body')` call |
| Test impact | Current mocks work | Must mock `locator().aria_snapshot` chain |
| AC alignment | Matches AC exactly | Requires AC revision |

## 4. Recommendation (confidence: .85)

~~**Block #855 until Playwright Python 1.59.0 is published to PyPI.**~~ Node.js 1.59.1 shipped ~April 4; Python typically follows within weeks. The snapshot tool is still a stub with no production callers — no urgency.

~~**Alternative (confidence: .75):**~~ Revise AC to `>=1.49.0` and use `page.locator('body').aria_snapshot()`. This unblocks immediately but requires updating both this task's AC and the #837 implementation plan (tests + tool code). Less clean.

Challenge: FALLBACK — blocking recommendation based on factual PyPI constraint, not controversial.

**Tier: T1 — Autonomous.** Config change with no architectural implications. Blocked by external dependency availability, not by a design decision.

### 4a. Resolution (2026-04-14)

The "alternative" (Option B) was the correct choice all along. `page.aria_snapshot()` in v1.59 is explicitly documented as *"equivalent to `page.locator('body').aria_snapshot()`"* — it's a convenience alias, not a new capability. The recommendation to block was wrong: waiting months for a convenience alias while the functionally identical API has been available since v1.49 is not justified.

**Applied fix:**
- `server.py`: `page.aria_snapshot()` → `page.locator("body").aria_snapshot()`
- `serve/browser/pyproject.toml`: `playwright>=1.40` → `playwright>=1.49`
- Test mocks: moved `aria_snapshot` from page mock to locator mock
- No breaking changes between v1.40 and v1.49 affect our codebase

**Lesson for future research:** When an API has an equivalent that already exists, prefer the available equivalent over blocking on a convenience alias. Assess both options on merit, not on AC alignment — the AC can be revised.

## 5. Follow-up Tasks

~~None needed — task #855 is already the correctly scoped follow-up. It should be unblocked and executed once playwright-python 1.59.0 appears on PyPI.~~

Completed — see §4a.
