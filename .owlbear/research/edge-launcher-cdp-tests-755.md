# Edge Launcher + CDP Connection Manager — Test Strategy Research

> **Owning task:** #755 — P1-03: Tests — Edge launcher + CDP connection manager
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

Task #755 (RED phase) defines failing tests for the Edge launcher and CDP connection
manager in the future `serve/browser/` package (`owlbear_browser`). Four test areas:
(1) Edge binary discovery, (2) CDP launch args, (3) connection lifecycle,
(4) SSO login redirect detection. All tests use mocked subprocess/Playwright.

Key questions: What module paths and class names should tests import? What mock
strategy matches project conventions? What security-critical behaviors must tests
verify?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | Playwright `connect_over_cdp` API | playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp | .95 |
| 2 | Chrome 136 `--remote-debugging-port` restriction | developer.chrome.com/blog/remote-debugging-port | .95 |
| 3 | CDP spike research #752 | .owlbear/research/cdp-spike-752.md | .90 |
| 4 | Brief — architect voice | .owlbear/briefs/draft-browser-knowledge-extraction/opinions/architect.md | .90 |
| 5 | Brief — security voice | .owlbear/briefs/draft-browser-knowledge-extraction/opinions/security.md | .90 |
| 6 | Browser automation research #264 | .owlbear/research/browser-automation.md | .85 |
| 7 | Existing test patterns | tests/test_process_supervisor.py, tests/test_voice_process_manager.py | .95 |
| 8 | v1 feature inventory | .owlbear/research/v1-feature-inventory.md §4.3 | .80 |

## 3. Analysis

### 3a. Module Structure (from Architect Voice + Package Conventions)

`serve/browser/` → `owlbear_browser`. Following `serve/knowledge/` → `owlbear_knowledge` pattern:

| Module | Responsibility | Key exports |
|--------|---------------|-------------|
| `owlbear_browser.launcher` | Edge binary discovery + subprocess launch | `find_edge_binary()`, `launch_edge()`, `build_launch_args()`, `EdgeNotFoundError` |
| `owlbear_browser.cdp` | CDP connection lifecycle + SSO detection | `CDPConnectionManager`, `CDPConnectionError`, `AuthenticationRequired` |

### 3b. Test File Placement

Project convention for RED-phase task tests: `tests/test_{feature}_{task_id}.py`.
Test file: `tests/test_edge_launcher_cdp_755.py`.

### 3c. Mock Strategy (from Existing Patterns)

| What to mock | How | Precedent |
|-------------|-----|-----------|
| Edge binary existence | `patch("shutil.which")` or `patch("pathlib.Path.exists")` | test_process_supervisor.py `_patch_which()` |
| subprocess.Popen (Edge launch) | `patch("subprocess.Popen")` with mock process | test_process_supervisor.py `_patch_spawn()` |
| Playwright `connect_over_cdp` | `AsyncMock` returning mock Browser | test_voice_process_manager.py async patterns |
| Page object (SSO detection) | `MagicMock` with `.url`, `.query_selector()` properties | Standard mock approach |
| httpx GET to CDP endpoint | `patch("httpx.AsyncClient")` or `AsyncMock` | test_bookmark_pipeline_136.py httpx patterns |

### 3d. Edge Binary Discovery — Windows Paths

| Path | Priority | Notes |
|------|----------|-------|
| `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` | 1 | Standard 64-bit install |
| `C:\Program Files\Microsoft\Edge\Application\msedge.exe` | 2 | Alternative install location |
| `EDGE_PATH` environment variable | 0 (override) | User/CI override |

Tests must verify: ordered path search, env var override, `EdgeNotFoundError` on miss.

### 3e. CDP Launch Args — Security-Critical Requirements

From brief security voice + Chrome 136 constraint:

| Arg | Requirement | Source |
|-----|------------|--------|
| `--remote-debugging-port=<port>` | Always present, defaults to 9222 | CDP spike §3.3 |
| `--remote-allow-origins=http://127.0.0.1:<port>` | Localhost only, never `*` | Security voice HR#4 |
| `--user-data-dir=<non-default-path>` | **Mandatory** (Chrome 136) | Chrome 136 blog post |
| No `--remote-allow-origins=*` | Wildcard must never appear | Security voice HR#4 |
| No `0.0.0.0` binding | Port binds to localhost only | Security voice HR#4 |

### 3f. Connection Lifecycle — Playwright CDP API

```python
browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", is_local=True, timeout=30000)
context = browser.contexts[0]  # default context carries SSO session
page = await context.new_page()  # or context.pages[0]
```

Tests: connect success, connect timeout, disconnect cleanup, reconnect after drop.

### 3g. SSO Detection Patterns (from CDP Spike §3.4)

| Pattern | Detection | Test approach |
|---------|-----------|---------------|
| URL redirect to IdP | `page.url` differs from target, matches IdP pattern | Mock `page.url` returning IdP URL |
| Login form present | Page contains password field | Mock `page.query_selector("input[type=password]")` |
| HTTP 401/403 | Response status code | Mock page response |

Fail-fast: `AuthenticationRequired` raised on detection, caller aborts remaining URLs.

### 3h. Test Class Structure

| Class | Area | Est. tests |
|-------|------|-----------|
| `TestFromAC_EdgeDiscovery` | Binary resolution, env override, not-found error | 5 |
| `TestFromAC_CDPLaunchArgs` | Port arg, allow-origins, user-data-dir, no wildcards | 6 |
| `TestFromAC_ConnectionLifecycle` | Connect, disconnect, reconnect, timeout | 5 |
| `TestFromAC_SSODetection` | URL redirect, login form, fail-fast, auth error type | 5 |
| **Total** | | **~21** |

## 4. Recommendation (.85 confidence)

Proceed with RED-phase test implementation following the structure in §3h. The module
paths (`owlbear_browser.launcher`, `owlbear_browser.cdp`) align with the architect
voice's package design and project naming conventions. Mock strategy follows established
project patterns.

**Security-critical tests** (§3e) are non-negotiable — Chrome 136 compliance and
localhost-only binding must be verified at the test level to prevent regressions.

**Tier: T1** — tests for an already-approved feature with complete brief and research.
No new decisions needed.

Challenge: FALLBACK — challenger not available. Self-challenge: could tests go in
`serve/browser/tests/` instead of root `tests/`? Answer: `serve/browser/` doesn't exist
yet. Per project convention, RED-phase tests for non-existent packages go in root
`tests/` with task-ID suffix. The builder creates the package structure.

## 5. Follow-up Tasks

None needed beyond the task itself (#755) advancing to backlog for test-writer pickup.
The task already has concrete AC. No decomposition required — single test file, ~21 tests.
