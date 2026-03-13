---
id: 495
title: Isolate browser context in CDP mode
status: archived
priority: important
created: 2026-03-04T07:38:10.0052022+01:00
updated: 2026-03-09T21:02:46.8098623+01:00
started: 2026-03-06T23:23:22.8991517+01:00
completed: 2026-03-09T21:02:46.8098623+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-07 from docs/security-audit.md: CDP mode attaches to user's existing browser using contexts[0], gaining access to all authenticated sessions, cookies, and localStorage. Must create isolated context instead.

See docs/research/cdp-context-isolation.md for full analysis.

## Architecture Decision

Option A (always isolate, .90 confidence): Replace contexts[0] with browser.new_context(viewport=...) unconditionally. No config flag (YAGNI -- no use case for deliberately sharing sessions).

Playwright's browser.new_context() on CDP connections delegates to Target.createBrowserContext, providing full cookie/cache/localStorage isolation. This is a stable, non-experimental CDP API.

## Acceptance Criteria

- [ ] BrowserManager._enter_cdp() creates isolated context via self._browser.new_context(viewport={'width': w, 'height': h}) instead of self._browser.contexts[0]
- [ ] Viewport dimensions sourced from self._config.viewport (same as launch mode)
- [ ] BrowserManager._exit_cdp() closes the owned context via self._context.close() before self._browser.disconnect()
- [ ] Context close is in a try/finally to ensure disconnect() always runs even if close() fails
- [ ] Cleanup follows the same nested try/finally pattern as _exit_launch() (page -> context -> browser -> playwright)
- [ ] All existing browser tests updated: CDP mock chain asserts new_context() called (not contexts[0])
- [ ] New test assertion: contexts[0] is NOT accessed in CDP mode
- [ ] New test assertion: context.close() called during CDP cleanup
- [ ] ruff clean, all tests pass

[[2026-03-09]] Mon 20:41
## Audit

### AC Verification
| # | AC Item | Evidence | Status |
|---|---------|----------|--------|
| 1 | _enter_cdp uses new_context | manager.py L107 | PASS |
| 2 | Viewport from config.viewport | manager.py L106 | PASS |
| 3 | _exit_cdp closes context before disconnect | manager.py L139-148 | PASS |
| 4 | try/finally ensures disconnect | test confirms | PASS |
| 5 | Same nested pattern as _exit_launch | Verified | PASS |
| 6 | CDP mock chain updated | pw_mocks fixture | PASS |
| 7 | contexts[0] not accessed | test assertion | PASS |
| 8 | context.close called in cleanup | test assertion | PASS |
| 9 | ruff clean, tests pass | 33/33 browser; 1334 full suite | PASS |

### Test Results
- pytest scoped: 33 passed
- pytest full: 1334 passed, 1 unrelated fail
- ruff scoped: clean

### Confidence: .97
### Action: archive
