---
id: 868
title: 'RED: Tests for Playwright launcher + SSO extension discovery'
status: backlog
priority: critical
created: '2026-04-13T23:21:28.944487+00:00'
updated: '2026-04-13T23:21:28.944487+00:00'
tags:
- pivot
- phase-1
- scope:browser
- type:test
- tdd-red
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

CDP approach blocked by corporate Group Policy (`RemoteDebuggingAllowed=0`). Pivot to Playwright Chromium + Microsoft SSO extension validated in E2E PoC. See `.owlbear/research/cdp-spike-results.md`.

Replaces superseded #782 (old CDP launcher tests) and #760 (old content extractor + login redirect detection tests).

## Winning Architecture (from PoC)

```python
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=str(PROFILE_DIR),
    headless=False,
    args=[
        f"--disable-extensions-except={sso_ext_path}",
        f"--load-extension={sso_ext_path}",
    ],
)
```

- SSO extension ID: `ppnbnpeolgkicgegkbkbjmhlideopiji` (Microsoft Single Sign On)
- Extension source: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions\{ext_id}\{version}`
- Persistent profile: session cookies survive across launches
- No CDP port needed — Playwright controls its own Chromium binary

## Acceptance Criteria

1. Test file `tests/test_playwright_launcher_XXX.py` (XXX = this task ID)
2. Tests for `find_sso_extension() -> Path`:
   - Returns path when extension dir exists with version subfolder
   - Raises `SSOExtensionNotFoundError` when extension dir missing
   - Raises `SSOExtensionNotFoundError` when no version subfolders
   - Respects `SSO_EXTENSION_PATH` env var override
   - Env var override validates path exists (raises if not)
3. Tests for `build_playwright_args(sso_ext_path) -> list[str]`:
   - Includes `--disable-extensions-except={path}` and `--load-extension={path}`
   - Never includes `--remote-debugging-port` (CDP is dead)
   - Never includes `0.0.0.0` in any arg
4. Tests for `PlaywrightLauncher`:
   - `launch()` calls `playwright.chromium.launch_persistent_context()` with correct args
   - `launch()` passes `user_data_dir` to persistent context
   - `close()` calls `context.close()` and `playwright.stop()`
   - Context manager (`async with`) delegates to launch/close
   - `page` property returns first page from context
5. All tests FAIL at RED phase (modules don't exist yet or are stubs)
6. ruff clean

## Notes

- Reference PoC: `.owlbear/scratch/e2e-poc.py`
- `AuthenticationRequired` error may still be useful for Skyway first-login detection
- Cleaner pipeline (`owlbear_browser.cleaner.clean()`) is unchanged by pivot
- `owlbear_browser.extractor.extract_content()` is unchanged by pivot