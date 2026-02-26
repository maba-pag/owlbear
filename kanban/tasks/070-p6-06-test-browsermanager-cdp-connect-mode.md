---
id: 70
title: 'P6-06: Test BrowserManager CDP connect mode'
status: done
priority: high
created: 2026-02-26T23:30:51.9397243+01:00
updated: 2026-02-27T00:07:23.0154819+01:00
started: 2026-02-26T23:43:01.5542988+01:00
completed: 2026-02-27T00:07:23.0154819+01:00
tags:
    - phase-6
    - test
    - browser
depends_on:
    - 67
class: standard
---

## Acceptance Criteria

Test file: tests/test_browser_manager.py (extend existing file)

### CDP connect mode tests
- When config.cdp_endpoint is set, __aenter__ calls pw.chromium.connect_over_cdp(endpoint)
- Reuses existing browser context via browser.contexts[0] (not new_context)
- Opens new page in reused context
- Sets page timeout from config

### Fallback and error tests
- When cdp_endpoint is None, __aenter__ uses launch mode (existing behavior)
- When CDP endpoint unreachable, raises ConnectionError (no silent fallback)

### Mock pattern
- Extend existing pw_mocks fixture to support connect_over_cdp mock chain
- connect_over_cdp returns browser mock with pre-populated contexts list
- All existing launch-mode tests still pass with zero changes
