---
id: 869
title: 'GREEN: Implement Playwright launcher + SSO extension replacing Edge CDP'
status: backlog
priority: critical
created: '2026-04-13T23:21:47.239423+00:00'
updated: '2026-04-13T23:21:47.239423+00:00'
tags:
- pivot
- phase-1
- scope:browser
- tdd-green
parent: 751
depends_on:
- 868
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

CDP approach NO-GO. Implement Playwright persistent context + SSO extension approach validated in E2E PoC. This replaces `launcher.py`, `edge_launcher.py`, and `cdp.py` with a single Playwright-based launcher module.

Replaces superseded #787 (old CDP launcher implementation).

## Acceptance Criteria

1. New `serve/browser/src/owlbear_browser/playwright_launcher.py`:
   - `find_sso_extension() -> Path` — discovers Microsoft SSO extension from Chrome's managed extension dir (`%LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions\ppnbnpeolgkicgegkbkbjmhlideopiji\{version}`); respects `SSO_EXTENSION_PATH` env override; raises `SSOExtensionNotFoundError`
   - `build_playwright_args(sso_ext_path: Path) -> list[str]` — returns `[--disable-extensions-except=..., --load-extension=...]`; never includes CDP port or `0.0.0.0`
   - `PlaywrightLauncher` class — wraps `playwright.chromium.launch_persistent_context()` with SSO extension loading, persistent profile, async context manager
2. New `serve/browser/src/owlbear_browser/_errors.py` updates:
   - Add `SSOExtensionNotFoundError(RuntimeError)` 
   - Keep `AuthenticationRequired` (still used for Skyway first-login detection)
   - `EdgeNotFoundError` and `CDPConnectionError` can remain for backward compat but are no longer raised by new code
3. `serve/browser/src/owlbear_browser/__init__.py` updated:
   - Export `PlaywrightLauncher`, `find_sso_extension`, `SSOExtensionNotFoundError`
   - Keep existing exports for backward compat (gradual migration)
4. `serve/browser/src/owlbear_browser/fetcher.py` updated:
   - `BrowserContentFetcher.__init__` accepts a Playwright `BrowserContext` (not CDP manager)
   - `fetch(url)` uses `context.new_page()` → `page.goto(url)` → `page.content()` → `extract_content()`
5. All #868 RED tests pass
6. ruff clean

## Notes

- Reference PoC: `.owlbear/scratch/e2e-poc.py`, `.owlbear/scratch/multi-url-poc.py`
- Old Edge/CDP modules (`launcher.py`, `edge_launcher.py`, `cdp.py`) are NOT deleted in this task — cleanup is separate
- `headless=False` required (Group Policy: `HeadlessModeEnabled=0` on managed browsers; Playwright Chromium may or may not respect this but visible browser is acceptable)
- SharePoint never reaches `networkidle` — use `domcontentloaded` + reasonable wait